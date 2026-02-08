import cv2
import numpy as np
import os

class StyleTransferEngine:
    def __init__(self):
        self.net = None
        self.current_model = None

    def load_model(self, model_path):
        if model_path == self.current_model:
            return True
            
        if not os.path.exists(model_path):
            print(f"AI: Model file not found: {model_path}")
            return False
            
        try:
            # Try generic load (supports ONNX, Torch, Caffe, TF)
            self.net = cv2.dnn.readNet(model_path)
            
            # Try to use CUDA if available
            try:
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            except:
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                
            self.current_model = model_path
            return True
        except Exception as e:
            print(f"AI: Error loading model {model_path}: {e}")
            self.net = None
            self.current_model = None
            return False

    def process_frame(self, frame, strength=1.0):
        if not self.net:
            return frame

        h, w = frame.shape[:2]
        
        # Preprocessing (Mean subtraction for ImageNet)
        # Fast Neural Style usually uses these values.
        blob = cv2.dnn.blobFromImage(frame, 1.0, (w, h), (103.939, 116.779, 123.680), swapRB=False, crop=False)
        
        self.net.setInput(blob)
        out = self.net.forward()
        
        # Postprocessing
        out = out.reshape(3, out.shape[2], out.shape[3])
        out[0] += 103.939
        out[1] += 116.779
        out[2] += 123.680
        out = out.transpose(1, 2, 0)
        out = np.clip(out, 0, 255).astype(np.uint8)
        
        if strength < 1.0:
            # Blend with original
            return cv2.addWeighted(frame, 1.0 - strength, out, strength, 0)
            
        return out
