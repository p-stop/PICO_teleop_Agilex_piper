"""Latest-target subprocess workers: native solvers never block session I/O."""
from dataclasses import asdict
import multiprocessing as mp
import time


def _run(connection, model_config, options):
    try:
        from .pinocchio_model import PinocchioModel
        model = PinocchioModel(**model_config, weights=options.get('weights'))
        connection.send({'type':'ready', 'model_sha256':model.sha256})
        wrist = None
        if options.get('wrist_smooth_multiplier', 1) > 1 and options.get('wrist_smooth_q5_rad', 0) > 0 \
                and all(n in model.names for n in ('joint4', 'joint5', 'joint6')):
            wrist = tuple(model.names.index(n) for n in ('joint5', 'joint4', 'joint6'))
        previous, previous_token = None, None
        while True:
            goal = connection.recv()
            if goal is None: break
            token = goal['token']
            seed = previous if previous is not None and token == previous_token else goal['seed']
            scale = None
            # (c) Near the wrist singularity (|q5| small) joints 4 and 6 swap freely;
            # weigh their change relative to the previous solution more heavily.
            if wrist is not None and abs(seed[wrist[0]]) < options['wrist_smooth_q5_rad']:
                scale = [1.]*len(seed)
                for i in wrist[1:]: scale[i] = options['wrist_smooth_multiplier']
            result = model.ik(goal['target'], seed, max_ms=options['deadline_ms'],
                max_iterations=options['max_iterations'], allow_best_effort=options['allow_best_effort'],
                seed_tolerance_rad=options.get('seed_tolerance_rad',.005), smooth_scale=scale)
            if result.accepted: previous, previous_token = result.positions, token
            connection.send({'type':'result','token':token,'goal_seq':goal['seq'],
                'created_s':goal['created_s'],'result':asdict(result),'wrist_smooth':scale is not None})
    except (EOFError, BrokenPipeError): pass
    except Exception as exc:
        try: connection.send({'type':'error','error':str(exc)})
        except (EOFError, BrokenPipeError): pass
    finally: connection.close()


class SolverProcess:
    def __init__(self, model_config, options):
        context = mp.get_context('spawn')
        self.connection, child = context.Pipe()
        self.process = context.Process(target=_run,args=(child,model_config,options),daemon=True)
        self.process.start(); child.close()
        self.latest = self.result = None
        self.busy, self.ready, self.error = False, False, None
        self.started = self.sent_at = time.monotonic()
        self.hang_timeout = options.get('hang_timeout_s',2.)

    def request(self, goal):
        self.latest = goal

    def poll(self):
        now = time.monotonic()
        try:
            if self.connection.poll():
                message = self.connection.recv()
                if message['type'] == 'ready': self.ready = True
                elif message['type'] == 'error': self.error = message['error']
                else: self.result, self.busy = message, False
            if not self.process.is_alive() and not self.error:
                self.error = 'solver_process_exited'
            if self.busy and now-self.sent_at > self.hang_timeout:
                self.error = 'solver_hung'
            if not self.ready and now-self.started > 30:
                self.error = 'solver_start_timeout'
            if self.error: return
            if self.ready and not self.busy and self.latest is not None:
                self.connection.send(self.latest)
                self.latest = None
                self.busy, self.sent_at = True, now
        except (EOFError, BrokenPipeError, OSError) as exc:
            self.error = str(exc)

    def take_result(self):
        result, self.result = self.result, None
        return result

    def clear(self):
        # An in-flight result retains its old token and will be rejected.
        self.latest = self.result = None

    def close(self):
        self.latest = None
        if self.process.is_alive() and not self.busy:
            try: self.connection.send(None)
            except (BrokenPipeError, EOFError, OSError): pass
        self.process.join(timeout=.5)
        if self.process.is_alive(): self.process.terminate(); self.process.join(timeout=1)
        if self.process.is_alive(): self.process.kill(); self.process.join(timeout=1)
        self.connection.close()
