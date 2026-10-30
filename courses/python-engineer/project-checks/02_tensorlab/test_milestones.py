"""Python Engineer tensorlab contracts. See test bodies for the app-facing APIs."""
import importlib
import json
import math
import random
import pytest


def api():
    return importlib.import_module('tensorlab')


class TestMilestone2:
    def test_shapes_broadcast_and_gradient(self):
        t = api()
        x = t.Tensor([[1.,2.],[3.,4.]], requires_grad=True)
        b = t.Tensor([10.,20.], requires_grad=True)
        assert tuple(x.shape)==(2,2) and x.ndim==2 and x.size==4
        y=(x+b).sum(); y.backward()
        assert b.grad.tolist()==[2.,2.]
        assert x.grad.tolist()==[[1.,1.],[1.,1.]]
        assert x.T.tolist()==[[1.,3.],[2.,4.]]
        assert x.reshape(4).tolist()==[1.,2.,3.,4.]

    def test_matmul_and_detach(self):
        t=api();x=t.Tensor([[1.,2.]],requires_grad=True)
        assert (x@t.Tensor([[3.],[4.]])).tolist()==[[11.]]
        assert x.detach().requires_grad is False
        with t.no_grad(): assert (x+x).requires_grad is False


class TestMilestone3:
    def test_parameters_state_and_eval(self):
        t=api();layer=t.Linear(2,3)
        parameters=list(layer.parameters())
        assert parameters and all(p.requires_grad for p in parameters)
        assert tuple(layer(t.Tensor([[1.,2.]])).shape)==(1,3)
        state=json.loads(json.dumps(layer.state_dict()))
        other=t.Linear(2,3);other.load_state_dict(state)
        assert other.state_dict()==state
        model=t.Sequential(layer,t.Dropout(0.5));model.eval()
        assert model.training is False and layer.training is False
        assert model(t.Tensor([[1.,2.]])).tolist()==model(t.Tensor([[1.,2.]])).tolist()

    def test_embedding_and_normalization(self):
        t=api();embedded=t.Embedding(4,3)(t.Tensor([0,2]))
        assert tuple(embedded.shape)==(2,3)
        values=t.LayerNorm(3)(t.Tensor([[1.,2.,3.]]))
        assert abs(sum(values.tolist()[0]))<1e-5


class TestMilestone4:
    def test_losses_are_finite_and_correct(self):
        t=api()
        assert t.mse_loss(t.Tensor([1.,3.]),t.Tensor([2.,2.])).item()==pytest.approx(1.)
        value=t.cross_entropy(t.Tensor([[100.,-100.]]),t.Tensor([0])).item()
        assert math.isfinite(value) and value<1e-5
        assert math.isfinite(t.binary_cross_entropy(t.Tensor([0.2,0.8]),t.Tensor([0.,1.])).item())

    @pytest.mark.parametrize('name',['SGD','Adam'])
    def test_optimizer_decreases_loss(self,name):
        t=api();p=t.Parameter([3.]);opt=getattr(t,name)([p],lr=0.05)
        before=(p*p).sum().item()
        for _ in range(10):
            opt.zero_grad();(p*p).sum().backward();opt.step()
        assert (p*p).sum().item()<before

    def test_scheduler(self):
        t=api();opt=t.SGD([t.Parameter([1.])],lr=1.)
        scheduler=t.lr_scheduler.StepLR(opt,step_size=1,gamma=0.5);scheduler.step()
        assert opt.lr==pytest.approx(0.5)


class TestMilestone5:
    def test_loader_is_reproducible_and_gradcheck(self):
        t=api();data=list(range(11))
        a=list(t.DataLoader(data,batch_size=3,shuffle=True,seed=7))
        b=list(t.DataLoader(data,batch_size=3,shuffle=True,seed=7))
        assert a==b and sorted(x for batch in a for x in batch)==data
        assert t.gradcheck(lambda x:(x*x).sum(),[t.Tensor([1.,2.],requires_grad=True)])

    def test_xor_training_contract(self):
        t=api();random.seed(7)
        model=t.Sequential(t.Linear(2,8),t.Tanh(),t.Linear(8,1),t.Sigmoid())
        optimizer=t.Adam(list(model.parameters()),lr=0.05)
        callbacks=[]
        trainer=t.Trainer(model,optimizer=optimizer,loss=t.binary_cross_entropy)
        x=t.Tensor([[0.,0.],[0.,1.],[1.,0.],[1.,1.]])
        target=t.Tensor([[0.],[1.],[1.],[0.]])
        trainer.fit(x,target,max_epochs=2000,on_epoch_end=lambda epoch,loss:callbacks.append(loss))
        predictions=[float(row[0])>=0.5 for row in model(x).tolist()]
        assert predictions==[False,True,True,False]
        assert callbacks and len(callbacks)<=2000



class TestMilestone6:
    def test_backends_agree_for_values_and_gradients(self):
        t=api();outputs=[]
        try:
            for backend in ['python','numpy']:
                t.set_backend(backend)
                x=t.Tensor([[1.,2.],[3.,4.]],requires_grad=True)
                y=(x*x).sum();y.backward();outputs.append((y.item(),x.grad.tolist()))
            assert outputs[0]==outputs[1]
        finally: t.set_backend('python')

    @pytest.mark.benchmark
    def test_backend_benchmark(self):
        import time
        t=api()
        for backend in ['python','numpy']:
            t.set_backend(backend);x=t.Tensor([[1.]*16 for _ in range(256)],requires_grad=True)
            start=time.perf_counter();(x*x).sum().backward()
            print(backend,time.perf_counter()-start)
        t.set_backend('python')
