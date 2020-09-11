# pylint: disable=g-classes-have-attributes
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tensorflow.python.framework import ops
from tensorflow.python.keras.optimizer_v2 import optimizer_v2
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import resource_variable_ops
from tensorflow.python.training import training_ops
from tensorflow.python.util.tf_export import keras_export


@keras_export("keras.optimizers.SGD")
class SGD(optimizer_v2.OptimizerV2):
  r"""Gradient descent (with momentum) optimizer.
  Update rule for parameter `w` with gradient `g` when `momentum` is 0:
  ```python
  w = w - learning_rate * g
  ```
  Update rule when `momentum` is larger than 0:
  ```python
  velocity = momentum * velocity - learning_rate * g
  w = w * velocity
  ```
  When `nesterov=False`, this rule becomes:
  ```python
  velocity = momentum * velocity - learning_rate * g
  w = w + momentum * velocity - learning_rate * g
  ```
  Args:
    learning_rate: A `Tensor`, floating point value, or a schedule that is a
      `tf.keras.optimizers.schedules.LearningRateSchedule`, or a callable
      that takes no arguments and returns the actual value to use. The
      learning rate. Defaults to 0.01.
    momentum: float hyperparameter >= 0 that accelerates gradient descent
      in the relevant
      direction and dampens oscillations. Defaults to 0, i.e., vanilla gradient
      descent.
    nesterov: boolean. Whether to apply Nesterov momentum.
      Defaults to `False`.
    name: Optional name prefix for the operations created when applying
      gradients.  Defaults to `"SGD"`.
    **kwargs: Keyword arguments. Allowed to be one of
      `"clipnorm"` or `"clipvalue"`.
      `"clipnorm"` (float) clips gradients by norm; `"clipvalue"` (float) clips
      gradients by value.
  Usage:
  >>> opt = tf.keras.optimizers.SGD(learning_rate=0.1)
  >>> var = tf.Variable(1.0)
  >>> loss = lambda: (var ** 2)/2.0         # d(loss)/d(var1) = var1
  >>> step_count = opt.minimize(loss, [var]).numpy()
  >>> # Step is `- learning_rate * grad`
  >>> var.numpy()
  0.9
  >>> opt = tf.keras.optimizers.SGD(learning_rate=0.1, momentum=0.9)
  >>> var = tf.Variable(1.0)
  >>> val0 = var.value()
  >>> loss = lambda: (var ** 2)/2.0         # d(loss)/d(var1) = var1
  >>> # First step is `- learning_rate * grad`
  >>> step_count = opt.minimize(loss, [var]).numpy()
  >>> val1 = var.value()
  >>> (val0 - val1).numpy()
  0.1
  >>> # On later steps, step-size increases because of momentum
  >>> step_count = opt.minimize(loss, [var]).numpy()
  >>> val2 = var.value()
  >>> (val1 - val2).numpy()
  0.18
  Reference:
      - For `nesterov=True`, See [Sutskever et al., 2013](
        http://jmlr.org/proceedings/papers/v28/sutskever13.pdf).
  """

  _HAS_AGGREGATE_GRAD = True

  def __init__(self,
               learning_rate=0.01,
               weight_decay=0.0005,
               momentum=0.0,
               nesterov=False,
               name="SGD",
               **kwargs):
    super(SGD, self).__init__(name, **kwargs)
    self._set_hyper("learning_rate", kwargs.get("lr", learning_rate))
    self._set_hyper("decay", self._initial_decay)

    self._weight_decay = False
    if isinstance(weight_decay, ops.Tensor) or callable(weight_decay) or weight_decay > 0:
      self._weight_decay = True
    if isinstance(momentum, (int, float)) and (momentum < 0 or momentum > 1):
      raise ValueError("`weight_decay` must be between [0, 1].")
    self._set_hyper("weight_decay", weight_decay)

    self._momentum = False
    if isinstance(momentum, ops.Tensor) or callable(momentum) or momentum > 0:
      self._momentum = True
    if isinstance(momentum, (int, float)) and (momentum < 0 or momentum > 1):
      raise ValueError("`momentum` must be between [0, 1].")
    self._set_hyper("momentum", momentum)

    self.nesterov = nesterov

  def _create_slots(self, var_list):
    if self._momentum:
      for var in var_list:
        self.add_slot(var, "momentum")

    if self._weight_decay:
      for var in var_list:
        self.add_slot(var, "weight_decay")

  def _prepare_local(self, var_device, var_dtype, apply_state):
    super(SGD, self)._prepare_local(var_device, var_dtype, apply_state)
    apply_state[(var_device, var_dtype)]["momentum"] = array_ops.identity(
        self._get_hyper("momentum", var_dtype))
    apply_state[(var_device, var_dtype)]["weight_decay"] = array_ops.identity(
        self._get_hyper("weight_decay", var_dtype))

  def _resource_apply_dense(self, grad, var, apply_state=None):
    var_device, var_dtype = var.device, var.dtype.base_dtype
    coefficients = ((apply_state or {}).get((var_device, var_dtype))
                    or self._fallback_apply_state(var_device, var_dtype))

    if self._momentum:
      momentum_var = self.get_slot(var, "momentum")
      return training_ops.resource_apply_keras_momentum(
          var.handle,
          momentum_var.handle,
          coefficients["lr_t"],
          grad,
          coefficients["momentum"],
          use_locking=self._use_locking,
          use_nesterov=self.nesterov)
    else:
      return training_ops.resource_apply_gradient_descent(
          var.handle, coefficients["lr_t"], grad, use_locking=self._use_locking)

  def _resource_apply_sparse_duplicate_indices(self, grad, var, indices,
                                               **kwargs):
    if self._momentum:
      return super(SGD, self)._resource_apply_sparse_duplicate_indices(
          grad, var, indices, **kwargs)
    else:
      var_device, var_dtype = var.device, var.dtype.base_dtype
      coefficients = (kwargs.get("apply_state", {}).get((var_device, var_dtype))
                      or self._fallback_apply_state(var_device, var_dtype))

      return resource_variable_ops.resource_scatter_add(
          var.handle, indices, -grad * coefficients["lr_t"])

  def _resource_apply_sparse(self, grad, var, indices, apply_state=None):
    # This method is only needed for momentum optimization.
    var_device, var_dtype = var.device, var.dtype.base_dtype
    coefficients = ((apply_state or {}).get((var_device, var_dtype))
                    or self._fallback_apply_state(var_device, var_dtype))

    momentum_var = self.get_slot(var, "momentum")
    return training_ops.resource_sparse_apply_keras_momentum(
        var.handle,
        momentum_var.handle,
        coefficients["lr_t"],
        grad,
        indices,
        coefficients["momentum"],
        use_locking=self._use_locking,
        use_nesterov=self.nesterov)

  def get_config(self):
    config = super(SGD, self).get_config()
    config.update({
        "learning_rate": self._serialize_hyperparameter("learning_rate"),
        "decay": self._serialize_hyperparameter("decay"),
        "momentum": self._serialize_hyperparameter("momentum"),
        "nesterov": self.nesterov,
    })
    return config

# # [Reference] https://www.kdnuggets.com/2018/01/custom-optimizer-tensorflow.html

# from tensorflow.python.ops import control_flow_ops
# from tensorflow.python.ops import math_ops
# from tensorflow.python.ops import state_ops
# from tensorflow.python.framework import ops
# from tensorflow.python.training import optimizer
# import tensorflow as tf

# class AlexOptimizer(optimizer.Optimizer):
    
#     def __init__(self, learning_rate="learning_rate",alpha="alpha",beta="beta", weight_decay="weight_decay", use_locking=False, name="AlexOptimizer"):
#         super(AlexOptimizer, self).__init__(use_locking, name)
#         self._lr = learning_rate
#         self._wd = weight_decay
#         self._alpha = alpha
#         self._beta = beta
        
#         # Tensor versions of the constructor arguments, created in _prepare().
#         self._lr_t = None
#         self._wd_t = None
#         self._alpha_t = None
#         self._beta_t = None

#     def _prepare(self):
#         self._lr_t = ops.convert_to_tensor(self._lr, name="learning_rate")
#         self._wd_t = ops.convert_to_tensor(self._wd, name="weight_decay")
#         self._alpha_t = ops.convert_to_tensor(self._beta, name="alpha_t")
#         self._beta_t = ops.convert_to_tensor(self._beta, name="beta_t")

#     def _create_slots(self, var_list):
#         # Create slots for the first and second moments.
#         for v in var_list:
#             self._zeros_slot(v, "m", self._name)

#     def _apply_dense(self, grad, var):
#         lr_t = math_ops.cast(self._lr_t, var.dtype.base_dtype)
#         wd_t = math_ops.cast(self._wd_t, var.dtype.base_dtype)
#         alpha_t = math_ops.cast(self._alpha_t, var.dtype.base_dtype)
#         beta_t = math_ops.cast(self._beta_t, var.dtype.base_dtype)

#         eps = 1e-7 #cap for moving average
        
#         m = self.get_slot(var, "m")
#         m_t = m.assign(tf.maximum(beta_t * m + eps, tf.abs(grad)))

#         var_update = state_ops.assign_sub(var, lr_t*grad*tf.exp( tf.log(alpha_t)*tf.sign(grad)*tf.sign(m_t))) #Update 'ref' by subtracting 'value
#         #Create an op that groups multiple operations.
#         #When this op finishes, all ops in input have finished
#         return control_flow_ops.group(*[var_update, m_t])

#     def _apply_sparse(self, grad, var):
#         raise NotImplementedError("Sparse gradient updates are not supported.")