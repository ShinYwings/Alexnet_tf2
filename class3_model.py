import tensorflow as tf
from tensorflow.keras import Model
import tensorflow.keras
import BN_refer as bn
# class lrn(tf.keras.layers.Layer):
#     def __init__(self, depth_radius="depth_radius", bias="bias", alpha= "alpha", beta= "beta"):
#         super(lrn, self).__init__()
#         self.depth_radius = depth_radius
#         self.bias = bias
#         self.alpha = alpha
#         self.beta = beta

#     def call(self, input):
#         return tf.nn.local_response_normalization(input, depth_radius=self.depth_radius, bias=self.bias, alpha= self.alpha, beta= self.beta)

class mulLayer(tf.keras.layers.Layer):
    def __init__(self, weight_init="weight_init"):
        super(mulLayer, self).__init__()
        self.weight_init = weight_init

    def call(self, input):
        return tf.scalar_mul(self.weight_init,input)

class mAlexNet(Model):
    def __init__(self, LRN_INFO, NUM_CLASSES):

        super(mAlexNet, self).__init__()

        self.radius, self.alpha, self.beta, self.bias = LRN_INFO

        self.conv1 = tf.keras.layers.Conv2D(96, kernel_size=(11,11), input_shape = (227,227, 3),
                                            strides=(4,4), padding="valid", 
                                            activation='relu')
        self.conv2 = tf.keras.layers.Conv2D(256,kernel_size=(5,5), strides=(1,1), padding="same",
                                            activation='relu')
        self.conv3 = tf.keras.layers.Conv2D(384,kernel_size=(3,3), strides=(1,1), padding="same",
                                            activation='relu')
        self.conv4 = tf.keras.layers.Conv2D(384,kernel_size=(3,3), strides=(1,1), padding="same",
                                            activation='relu')
        self.conv5 = tf.keras.layers.Conv2D(256,kernel_size=(3,3), strides=(1,1), padding="same",
                                            activation='relu')
        
        self.pool1 = tf.keras.layers.MaxPool2D(pool_size=(3,3), strides=(2,2), padding="valid")
        self.pool2 = tf.keras.layers.MaxPool2D(pool_size=(3,3), strides=(2,2), padding="valid")
        self.pool3 = tf.keras.layers.MaxPool2D(pool_size=(3,3), strides=(2,2), padding="valid")

        # self.lrn1 = lrn(depth_radius=self.radius, alpha=self.alpha, beta=self.beta, bias=self.bias)
        # self.lrn2 = lrn(depth_radius=self.radius, alpha=self.alpha, beta=self.beta, bias=self.bias)
        # self.lrn3 = lrn(depth_radius=self.radius, alpha=self.alpha, beta=self.beta, bias=self.bias)
        self.bn1 = tf.keras.layers.BatchNormalization()
        self.bn1_2 = bn.BatchNormalization()
        self.bn2 = tf.keras.layers.BatchNormalization()
        self.bn3 = tf.keras.layers.BatchNormalization()

        self.flatten = tf.keras.layers.Flatten()
        self.fc1 = tf.keras.layers.Dense(4096,activation='relu')
        self.dropout1 = tf.keras.layers.Dropout(0.2)
        self.fc2 = tf.keras.layers.Dense(4096, activation='relu')
        self.dropout2 = tf.keras.layers.Dropout(0.2)

        self.fc3 = tf.keras.layers.Dense(NUM_CLASSES, activation='softmax')

        self.mul1 = mulLayer(weight_init=0.8)
        self.mul2 = mulLayer(weight_init=0.8)

    def call(self, x, training=None):
        
        # 1st layer
        # cnv1 = self.conv1(x)
        # lrn1 = self.lrn1(cnv1)
        # mp1 = self.pool1(lrn1)

        cnv1 = self.conv1(x)
        mp1 = self.pool1(cnv1)
        # bn1 = self.bn1(mp1, training = training)
        bn1_2, beta, gamma = self.bn1_2(mp1, training = training)

        # 2nd layer
        # cnv2 = self.conv2(mp1)
        # lrn2 = self.lrn2(cnv2)
        # mp2 = self.pool2(lrn2)

        cnv2 = self.conv2(bn1_2)
        mp2 = self.pool2(cnv2)
        bn2 = self.bn2(mp2, training = training)

        # 3rd layer
        # cnv3 = self.conv3(mp2)
        cnv3 = self.conv3(bn2)

        # 4th layer
        cnv4 = self.conv4(cnv3)
        
        # 5th layer
        # cnv5 = self.conv5(cnv4)
        # lrn3 = self.lrn3(cnv5)
        # mp3 = self.pool3(lrn3)

        cnv5 = self.conv5(cnv4)
        mp3 = self.pool3(cnv5)
        bn3 = self.bn3(mp3, training = training)
        
        # ft = self.flatten(mp3)
        ft = self.flatten(bn3)

        fcl1 = self.fc1(ft)
        if training:
            do1 = self.dropout1(fcl1, training= training)
            fcl2 = self.fc2(do1)
            do2 = self.dropout2(fcl2, training= training)
            fcl3 = self.fc3(do2)

        else:
            # multiply their outputs by 0.5
            mul1 = self.mul1(fcl1)
            fcl2 = self.fc2(mul1)
            mul2 = self.mul2(fcl2)
            fcl3 = self.fc3(mul2)

        return beta, gamma, fcl3