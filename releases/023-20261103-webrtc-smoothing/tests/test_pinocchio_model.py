import time
import pytest

pytest.importorskip('pinocchio')
np=pytest.importorskip('numpy')

from robot_infra.pinocchio_model import PinocchioModel
from robot_infra.kinematics import SerialModel
from robot_infra.solver_worker import SolverProcess


@pytest.fixture
def model_config(tmp_path):
    text='<robot name="synthetic"><link name="base"/>'
    for i,axis in enumerate(('0 0 1','0 1 0','0 1 0'),1):
        parent='base' if i==1 else f'l{i-1}'
        text+=f'<link name="l{i}"/><joint name="j{i}" type="revolute"><parent link="{parent}"/><child link="l{i}"/><origin xyz="{0 if i==1 else .4} 0 0"/><axis xyz="{axis}"/><limit lower="-2" upper="2" velocity="2" effort="10"/></joint>'
    text+='<link name="tip"/><joint name="tool" type="fixed"><parent link="l3"/><child link="tip"/><origin xyz=".4 0 0"/></joint></robot>'
    path=tmp_path/'arm.urdf';path.write_text(text)
    return {'path':str(path),'base':'base','tip':'tip','joint_names':['j1','j2','j3']}


def test_pinocchio_fk_matches_independent_chain(model_config):
    m=PinocchioModel(**model_config);other=SerialModel(**model_config)
    for q in ([0,0,0],[.4,-.7,.3],[-1.,1.,-.5]):
        assert np.allclose(m.fk(q),other.fk(q),atol=1e-10)


def test_pinocchio_scipy_local_target_and_unreachable(model_config):
    m=PinocchioModel(**model_config,weights={'smooth':0.,'posture':0.})
    target=m.fk([.32,-.38,.18]);r=m.ik(target,[.3,-.4,.2],max_ms=500)
    assert r.accepted and r.position_error_m<.003 and r.orientation_error_rad<.03
    target[0][3]=10
    r=m.ik(target,[.3,-.4,.2],max_ms=500,allow_best_effort=False)
    assert not r.accepted and all(lo<=v<=hi for v,(lo,hi) in zip(r.positions,m.limits))


def test_relative_pose_rotation_is_not_head_motion(model_config):
    m=PinocchioModel(**model_config);pose=m.fk([.2,-.3,.1])
    hand0={'position_m':[0,0,0],'orientation_xyzw':[0,0,0,1]}
    hand={'position_m':[.1,.2,.3],'orientation_xyzw':[0,0,np.sin(.1),np.cos(.1)]}
    target=m.relative_target(pose,hand0,hand,[[1,0,0],[0,1,0],[0,0,1]],1.,True)
    assert np.allclose(np.asarray(target)[:3,3]-np.asarray(pose)[:3,3],[.1,.2,.3])
    assert not np.allclose(np.asarray(target)[:3,:3],np.asarray(pose)[:3,:3])


def test_worker_runs_off_thread_and_cleans_process(model_config):
    options={'deadline_ms':50,'max_iterations':40,'allow_best_effort':True,'hang_timeout_s':2.}
    worker=SolverProcess(model_config,options)
    try:
        until=time.monotonic()+15
        while not worker.ready and not worker.error and time.monotonic()<until:worker.poll();time.sleep(.01)
        assert worker.ready,worker.error
        model=PinocchioModel(**model_config)
        worker.request({'target':model.fk([.32,-.38,.18]),'seed':[.3,-.4,.2],'created_s':time.monotonic(),'seq':1,'token':'test'})
        until=time.monotonic()+3;result=None
        while result is None and not worker.error and time.monotonic()<until:
            worker.poll();result=worker.take_result();time.sleep(.005)
        assert result and result['token']=='test' and result['result']['accepted']
    finally:worker.close()
    assert not worker.process.is_alive()


def test_smooth_scale_keeps_weighted_joint_near_seed(model_config):
    m=PinocchioModel(**model_config,weights={'smooth':1.,'posture':0.})
    seed=[.3,-.4,.2];target=m.fk([.5,-.6,.4])
    plain=m.ik(target,seed,max_ms=500)
    heavy=m.ik(target,seed,max_ms=500,smooth_scale=[1000.,1.,1.])
    assert abs(heavy.positions[0]-seed[0])<abs(plain.positions[0]-seed[0])
    with pytest.raises(ValueError,match='smooth_scale'):m.ik(target,seed,smooth_scale=[1.,0.,1.])


def test_worker_applies_wrist_smoothing_only_near_q5_zero(tmp_path):
    text='<robot name="six"><link name="base"/>'
    axes=('0 0 1','0 1 0','0 1 0','1 0 0','0 1 0','1 0 0')
    for i,axis in enumerate(axes,1):
        parent='base' if i==1 else f'l{i-1}'
        text+=f'<link name="l{i}"/><joint name="joint{i}" type="revolute"><parent link="{parent}"/><child link="l{i}"/><origin xyz="{0 if i==1 else .2} 0 0"/><axis xyz="{axis}"/><limit lower="-2.5" upper="2.5" velocity="2" effort="10"/></joint>'
    text+='<link name="tip"/><joint name="tool" type="fixed"><parent link="l6"/><child link="tip"/><origin xyz=".1 0 0"/></joint></robot>'
    path=tmp_path/'six.urdf';path.write_text(text)
    config={'path':str(path),'base':'base','tip':'tip','joint_names':[f'joint{i}' for i in range(1,7)]}
    options={'deadline_ms':80,'max_iterations':40,'allow_best_effort':True,'hang_timeout_s':2.,
             'wrist_smooth_q5_rad':.15,'wrist_smooth_multiplier':10.}
    worker=SolverProcess(config,options);model=PinocchioModel(**config)
    try:
        until=time.monotonic()+15
        while not worker.ready and not worker.error and time.monotonic()<until:worker.poll();time.sleep(.01)
        assert worker.ready,worker.error
        flags=[]
        for k,seed in enumerate(([.1,-.2,.3,.1,0.,.1],[.1,-.2,.3,.1,.6,.1])):
            worker.request({'target':model.fk(seed),'seed':seed,'created_s':time.monotonic(),'seq':k,'token':f't{k}'})
            until=time.monotonic()+3;result=None
            while result is None and not worker.error and time.monotonic()<until:
                worker.poll();result=worker.take_result();time.sleep(.005)
            assert result,worker.error
            flags.append(result['wrist_smooth'])
        assert flags==[True,False]
    finally:worker.close()
