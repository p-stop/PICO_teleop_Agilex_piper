"""Quantify teleop jitter vs end-effector height from a robot-infra run journal."""
import glob, json, sys
import numpy as np
from robot_infra.pinocchio_model import PinocchioModel

run = sys.argv[1]
cfg = json.load(open(run + '/effective-config.json'))
m = cfg['model']
model = PinocchioModel(m['path'], m['base'], m['tip'], m['joint_names'])
files = sorted(glob.glob(run + '/episode/events*.jsonl'), key=lambda p: (p.count('.'), p))
fb = {'left': [], 'right': []}; cmd = {'left': [], 'right': []}; res = {'left': [], 'right': []}
raw = []; teleop = []; intents = {}; state = None; t_state = None
for f in files:
    for line in open(f):
        if '"kind": "session_state"' in line and 'TELEOP' not in line and state != 'TELEOP' and False: pass
        if '"kind": "camera' in line or '"kind": "pose_feedback"' in line: continue
        e = json.loads(line); k = e['kind']; p = e['payload']; t = e['host_monotonic_ns'] * 1e-9
        if k == 'session_state':
            if state == 'TELEOP': teleop.append((t_state, t))
            state, t_state = p['state'], t
        elif k == 'feedback': fb[p['side']].append((t, p['q']))
        elif k == 'command' and 'q' in p and p.get('operation') is None: cmd[p['side']].append((t, p['q']))
        elif k == 'intent': intents[(p['side'], p['seq'])] = [row[3] for row in p['target'][:3]]
        elif k == 'motion_result' and p.get('usable') and (p['side'], p['goal_seq']) in intents: res[p['side']].append((t, p['result']['positions'], p['result']['reason'], p['result']['position_error_m'], p['result']['orientation_error_rad'], intents[(p['side'], p['goal_seq'])]))
        elif k == 'raw_input': raw.append(t)
if state == 'TELEOP': teleop.append((t_state, 1e18))
inside = lambda t: any(a <= t <= b for a, b in teleop)
print('run', run.split('/')[-1], 'teleop windows', [(round(b - a, 1) if b < 1e17 else 'open') for a, b in teleop])
rt = np.array([t for t in raw if inside(t)])
if len(rt) > 2: print('raw_input rate %.1f Hz, dt p50 %.1f ms p95 %.1f ms max %.0f ms' % (1 / np.median(np.diff(rt)), 1e3*np.median(np.diff(rt)), 1e3*np.percentile(np.diff(rt), 95), 1e3*np.diff(rt).max()))
for side in ('left', 'right'):
    F = [(t, q) for t, q in fb[side] if inside(t)]
    C = [(t, q) for t, q in cmd[side] if inside(t)]
    R = [r for r in res[side] if inside(r[0])]
    if len(C) < 50: print(side, 'too few commands', len(C)); continue
    ft = np.array([t for t, _ in F]); fq = np.array([q for _, q in F])
    ct = np.array([t for t, _ in C]); cq = np.array([q for _, q in C])
    reasons = {}
    for r in R: reasons[r[2]] = reasons.get(r[2], 0) + 1
    print(f'== {side}: feedback {len(F)} ({1/np.median(np.diff(ft)):.0f} Hz), commands {len(C)} ({1/np.median(np.diff(ct)):.0f} Hz), IK results {len(R)} {reasons}')
    # tip height & HF jitter (deviation from 0.25 s moving average) on feedback
    z = np.array([model.fk(q)[2][3] for q in fq])
    xyz = np.array([[r[3] for r in model.fk(q)[:3]] for q in fq])
    w = max(3, int(round(.25 / np.median(np.diff(ft)))))
    k = np.ones(w) / w
    def hf(a): return a - np.vstack([np.convolve(a[:, j], k, 'same') for j in range(a.shape[1])]).T
    qhf = hf(fq)[w:-w]; phf = hf(xyz)[w:-w]; zz = z[w:-w]
    # command HF jitter
    wc = max(3, int(round(.25 / np.median(np.diff(ct)))))
    kc = np.ones(wc) / wc
    chf = (cq - np.vstack([np.convolve(cq[:, j], kc, 'same') for j in range(6)]).T)[wc:-wc]
    cz = np.interp(ct, ft, z)[wc:-wc]
    # command velocity sign reversals per second (chatter)
    dv = np.diff(cq, axis=0); rev = (np.sign(dv[1:]) * np.sign(dv[:-1]) < 0) & (np.abs(dv[1:]) > 1e-4)
    w1 = max(3, int(round(1. / np.median(np.diff(ft))))); k1 = np.ones(w1)/w1
    lf = (xyz - np.vstack([np.convolve(xyz[:, j], k1, 'same') for j in range(3)]).T)[w1:-w1] - hf(xyz)[w1:-w1]
    lz = z[w1:-w1]
    print('   tip z range %.3f..%.3f m' % (z.min(), z.max()))
    edges = np.quantile(z, [0, .25, .5, .75, 1])
    print('   z-bin(m)         fb joint HF rms(mrad) per joint            fb tip HF rms(mm) | cmd joint HF rms(mrad)')
    for a, b in zip(edges[:-1], edges[1:]):
        s = (zz >= a) & (zz <= b); sc = (cz >= a) & (cz <= b)
        if s.sum() < 10: continue
        jr = 1e3 * np.sqrt((qhf[s] ** 2).mean(0)); pr = 1e3 * np.sqrt((phf[s] ** 2).sum(1).mean())
        cr = 1e3 * np.sqrt((chf[sc] ** 2).mean(0)) if sc.sum() > 10 else np.full(6, np.nan)
        s1 = (lz >= a) & (lz <= b); lfr = 1e3*np.sqrt((lf[s1]**2).sum(1).mean()) if s1.sum() > 10 else np.nan
        print('   [1-4Hz tip rms %.2f mm] ' % lfr, end='')
        print('   %.3f-%.3f  %s  %.2f | %s' % (a, b, ' '.join('%5.2f' % v for v in jr), pr, ' '.join('%5.2f' % v for v in cr)))
    print('   cmd velocity reversals/s per joint:', ' '.join('%.1f' % v for v in rev.sum(0) / (ct[-1] - ct[0])))
    # IK amplification: joint change per mm of target change, binned by height
    if len(R) > 20:
        rq = np.array([r[1] for r in R]); rt_ = np.array([r[0] for r in R])
        pe = np.array([r[3] for r in R]); oe = np.array([r[4] for r in R]); tgt = np.array([r[5] for r in R])
        dtgt = np.linalg.norm(np.diff(tgt, axis=0), axis=1); dqq = np.abs(np.diff(rq, axis=0)).max(1)
        still = dtgt < .001
        print('   IK: pos err p50/p95 %.1f/%.1f mm, ori err p50/p95 %.3f/%.3f rad; while target moved <1mm: joint step p50/p95/max %.1f/%.1f/%.1f mrad (n=%d)' % (1e3*np.median(pe), 1e3*np.percentile(pe,95), np.median(oe), np.percentile(oe,95), 1e3*np.median(dqq[still]) if still.any() else np.nan, 1e3*np.percentile(dqq[still],95) if still.any() else np.nan, 1e3*dqq[still].max() if still.any() else np.nan, still.sum()))
        rz = np.interp(rt_, ft, z)
        dq = np.abs(np.diff(rq, axis=0)).max(1)
        J = []
        for q in rq[::max(1, len(rq)//400)]:
            import pinocchio as pin
            d = model._data(); qq = model._q(q)
            Jm = pin.computeFrameJacobian(model.model, d, qq, model.tip_id, pin.ReferenceFrame.LOCAL_WORLD_ALIGNED)[:, model.velocity_indices]
            sv = np.linalg.svd(Jm[:3])[1]
            J.append((model.fk(q)[2][3], sv[-1], np.linalg.cond(Jm)))
        J = np.array(J)
        for a, b in zip(edges[:-1], edges[1:]):
            s = (J[:, 0] >= a) & (J[:, 0] <= b); s2 = (rz[1:] >= a) & (rz[1:] <= b)
            if s.sum(): print('   z %.3f-%.3f: min pos-singular value %.3f m/rad, cond(J6) %.0f, IK step p95 %.1f mrad' % (a, b, J[s, 1].mean(), np.median(J[s, 2]), 1e3*np.percentile(dq[s2], 95) if s2.sum() else np.nan))
