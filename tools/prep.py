import sys, types, cv2, json, numpy as np, torch
import torchvision.transforms.functional as F
m = types.ModuleType('torchvision.transforms.functional_tensor'); m.rgb_to_grayscale = F.rgb_to_grayscale; sys.modules['torchvision.transforms.functional_tensor'] = m
from facexlib.parsing import init_parsing_model
from facexlib.detection import init_detection_model
par = init_parsing_model('bisenet', device='cpu'); det = init_detection_model('retinaface_resnet50', half=False, device='cpu')
for n in ['himanshu', 'aman', 'charan']:
    img = cv2.imread(f'out/{n}.png'); H, W = img.shape[:2]
    with torch.no_grad(): d = det.detect_faces(img, 0.8)
    d = max(d, key=lambda r: (r[2] - r[0]) * (r[3] - r[1])); lm = d[5:15].reshape(5, 2)
    bx = d[:4]; cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2 - (bx[3] - bx[1]) * 0.08; hs = 0.95 * max(bx[2] - bx[0], bx[3] - bx[1])      # parse a square centred on the face
    X0, Y0, X1, Y1 = int(cx - hs), int(cy - hs), int(cx + hs), int(cy + hs); pad = int(max(0, -X0, -Y0, X1 - W, Y1 - H)) + 2
    big = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REPLICATE); sq = big[Y0 + pad:Y1 + pad, X0 + pad:X1 + pad]
    x = cv2.resize(sq, (512, 512)); t = torch.from_numpy(x[:, :, ::-1].copy()).permute(2, 0, 1).float() / 255.0
    t = ((t - torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)) / torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)).unsqueeze(0)
    with torch.no_grad(): lab = par(t)[0].squeeze(0).argmax(0).numpy().astype(np.uint8)
    labsq = cv2.resize(lab, (sq.shape[1], sq.shape[0]), interpolation=cv2.INTER_NEAREST); labbig = np.zeros(big.shape[:2], np.uint8); labbig[Y0 + pad:Y1 + pad, X0 + pad:X1 + pad] = labsq
    lab = labbig[pad:pad + H, pad:pad + W]
    face = np.isin(lab, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]); hair = lab == 17; head = face | hair
    num, cc, st, _ = cv2.connectedComponentsWithStats(head.astype(np.uint8)); k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); head &= cc == k
    ys, xs = np.where(head); fy, fx = np.where(face & head)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), fy.max()          # bottom = the chin, not the neck
    hairc = np.median(img[hair & head], 0); skinc = np.median(img[lab == 1], 0)
    eye_y = (lm[0, 1] + lm[1, 1]) / 2
    out = img.copy().astype(np.float32); yy = np.arange(H)[:, None] * np.ones((1, W))
    fill = np.where((yy < eye_y + (y1 - eye_y) * 0.35)[..., None], hairc[None, None, :], skinc[None, None, :])
    a = cv2.GaussianBlur(head.astype(np.float32), (0, 0), 2.5)[..., None]
    out = out * a + fill * (1 - a)
    crop = out[y0:y1 + 1, x0:x1 + 1].clip(0, 255).astype(np.uint8); h, w = crop.shape[:2]
    S_ = 768 / h; crop = cv2.resize(crop, (int(round(w * S_)), 768), interpolation=cv2.INTER_LANCZOS4)
    cv2.imwrite(f'out/{n}_headtex.png', crop)
    uv = lambda p: [float((p[0] - x0) / (x1 - x0)), float((p[1] - y0) / (y1 - y0))]
    meta = dict(aspect=float((x1 - x0) / (y1 - y0)), eyeA=uv(lm[0]), eyeB=uv(lm[1]), nose=uv(lm[2]), mouth=uv((lm[3] + lm[4]) / 2), hair=[int(c) for c in hairc[::-1]], skin=[int(c) for c in skinc[::-1]], hairline=float((fy.min() - y0) / (y1 - y0)))
    json.dump(meta, open(f'out/{n}_head.json', 'w')); print(n, meta)
