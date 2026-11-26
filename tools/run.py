import sys, types, cv2, os
import torchvision.transforms.functional as F
m = types.ModuleType('torchvision.transforms.functional_tensor'); m.rgb_to_grayscale = F.rgb_to_grayscale; sys.modules['torchvision.transforms.functional_tensor'] = m
from gfpgan import GFPGANer
g = GFPGANer(model_path='https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth', upscale=4, arch='clean', channel_multiplier=2, bg_upsampler=None, device='cpu')
for n in ['aman', 'charan', 'himanshu']:
    img = cv2.imread(f'in/{n}.png'); crops, faces, out = g.enhance(img, has_aligned=False, only_center_face=True, paste_back=True, weight=0.6)
    print(n, 'faces', len(faces), 'out', None if out is None else out.shape)
    if out is not None: cv2.imwrite(f'out/{n}.png', out)
    if faces: cv2.imwrite(f'out/{n}_face512.png', faces[0])
