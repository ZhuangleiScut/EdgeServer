# EdgeServer

EdgeServer是负责处理树莓派请求的server。

## head pose 
https://github.com/laodar/cnn_head_pose_estimator
### Requirement

-opencv

    only tested on 2.4.9.1

-mxnet

    only tested on 0.7.0

-mtcnn

    I use https://github.com/pangyupo/mxnet_mtcnn_face_detection to do face cropping and alignment

    padding = 0.27,desired_size = 64
