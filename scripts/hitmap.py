import ROOT
import sys
import os

def plot_hitmaps(root_file_path):
    # ROOT 파일 열기
    root_file = ROOT.TFile.Open(root_file_path)
    root_file_name = os.path.basename(root_file_path)[:-5]
    if not root_file or root_file.IsZombie():
        print(f"Failed to open {root_file_path}")
        return

    # Hitmaps 디렉토리 열기
    hitmaps_dir = root_file.Get("Hitmaps")
    if not hitmaps_dir:
        print("TDirectory 'Hitmaps' not found.")
        return

    # 캔버스 생성
    canvas = ROOT.TCanvas("canvas", "Hitmaps", 2000, 1000)

    # Hitmaps 디렉토리의 모든 키 가져오기
    keys = hitmaps_dir.GetListOfKeys()
    babyMOSS_hitmaps = {}
    for key in keys:
        detector_name = key.GetName()
        detector_dir = hitmaps_dir.Get(detector_name)
        
        if not isinstance(detector_dir, ROOT.TDirectoryFile):
            continue

        # ALPIDE의 경우 처리
        if detector_name.startswith("ALPIDE"):
            hitmap_name = f"h_hitmap_{detector_name}"
            hitmap = detector_dir.Get(hitmap_name)

            canvas.cd()
            hitmap.Draw("COLZ")
            canvas.Update()
            canvas.SaveAs(f"./fig/{root_file_name}_{detector_name}.pdf")

        # babyMOSS의 경우 처리
        elif "reg" in detector_name:
            det_index = int(detector_name.split('_')[-1])
            reg_index = int(detector_name.split('_reg')[1].split('_')[0])

            hitmap_name = f"h_hitmap_{detector_name}"
            hitmap = detector_dir.Get(hitmap_name)
            if "bb" in detector_name: 
                hitmap.SetTitle(f"BB_reg{reg_index}")
                reg_index = reg_index + 4
 # Y축 데이터 반전
                hitmap.GetYaxis().SetTitle("320-Y")
                flipped_hitmap = hitmap.Clone(f"flipped_{hitmap.GetName()}")
                y_bins = hitmap.GetNbinsY()
                for x_bin in range(1, hitmap.GetNbinsX() + 1):
                    for y_bin in range(1, y_bins + 1):
                        flipped_hitmap.SetBinContent(x_bin, y_bins - y_bin + 1, hitmap.GetBinContent(x_bin, y_bin))

                babyMOSS_hitmaps[(det_index, reg_index)] = flipped_hitmap

            else:
                hitmap.SetTitle(f"TB_reg{reg_index}")
                babyMOSS_hitmaps[(det_index, reg_index)] = hitmap

        else:
            continue


    for det_index in set(det for det, reg in babyMOSS_hitmaps):  # 각 detector index (det_index) 순회
        # 각 detector마다 새로운 canvas 생성
        canvas_name = f"canvas_{det_index}"
        individual_canvas = ROOT.TCanvas(canvas_name, canvas_name, 2000, 1000)
        individual_canvas.Divide(4, 2)  # Divide layout 설정
        
        # 각 detector에 대해 여러 region 순회
        for reg_index in set(reg for det, reg in babyMOSS_hitmaps if det == det_index):  # 해당 det_index에 대해 reg_index 순회
            individual_canvas.cd(reg_index + 1)  # 각 region에 해당하는 pad 선택
            
            # (det_index, reg_index)에 해당하는 hitmap을 그리기
            babyMOSS_hitmaps[(det_index, reg_index)].Draw("COLZ")
            ROOT.gPad.SetRightMargin(0.14)  # Right margin을 조정
        
        # 각 detector별 canvas 저장
        individual_canvas.SaveAs(f"./fig/{root_file_name}_babyMOSS_{det_index}.pdf")
        individual_canvas.Draw()

            


    # 파일 닫기
    root_file.Close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python plot_hitmaps.py <input_root_file>")
        sys.exit(1)

    root_file_path = sys.argv[1]

    ROOT.gStyle.SetOptStat(0)       # 원하는 statbox 옵션 설정 (e.g., 1110: entries, mean, RMS)
    ROOT.gStyle.SetFillStyle(0)
    #ROOT.gStyle.SetStatFillStyle(0)        # statbox 배경 투명하게 (0 = 투명)

    plot_hitmaps(root_file_path)