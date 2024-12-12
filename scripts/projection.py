import ROOT
import sys

def plot_projection(root_file_path):
    # ROOT 파일 열기
    root_file = ROOT.TFile.Open(root_file_path)
    if not root_file or root_file.IsZombie():
        print(f"Failed to open {root_file_path}")
        return

    # projection 디렉토리 열기
    projection_dir = root_file.Get("Hitmaps")
    if not projection_dir:
        print("TDirectory 'Hitmaps' not found.")
        return

    # 캔버스 생성
    canvas = ROOT.TCanvas("canvas", "canvas", 500, 400)

    # projection 디렉토리의 모든 키 가져오기
    keys = projection_dir.GetListOfKeys()
    babyMOSS_projection = {}
    for key in keys:
        detector_name = key.GetName()
        detector_dir = projection_dir.Get(detector_name)
        
        if not isinstance(detector_dir, ROOT.TDirectoryFile):
            continue

        # ALPIDE의 경우 처리
        if detector_name.startswith("ALPIDE"):
            projection_name = f"h_hitYmap_{detector_name}"
            projection = detector_dir.Get(projection_name)

            canvas.cd()
            projection.Draw("HIST")
            canvas.Update()
            canvas.SaveAs(f"./fig/projY_{detector_name}.pdf")

        # babyMOSS의 경우 처리
        elif "reg" in detector_name:
            det_index = int(detector_name.split('_')[-1])
            reg_index = int(detector_name.split('_reg')[1].split('_')[0])

            projection_name = f"h_hitYmap_{detector_name}"
            projection = detector_dir.Get(projection_name)
            if "bb" in detector_name: 
                projection.SetTitle(f"BB_reg{reg_index}")
                reg_index = reg_index + 4
            else:
                projection.SetTitle(f"TB_reg{reg_index}")

            babyMOSS_projection[(det_index, reg_index)] = projection

        else:
            continue


    for det_index in set(det for det, reg in babyMOSS_projection):  # 각 detector index (det_index) 순회
        # 각 detector마다 새로운 canvas 생성
        canvas_name = f"canvas_{det_index}"
        _canvas = ROOT.TCanvas(canvas_name, canvas_name, 800, 400)
        _canvas.Divide(4, 2)  # Divide layout 설정
        
        # 각 detector에 대해 여러 region 순회
        for reg_index in set(reg for det, reg in babyMOSS_projection if det == det_index):  # 해당 det_index에 대해 reg_index 순회
            _canvas.cd(reg_index + 1)  # 각 region에 해당하는 pad 선택
            
            # (det_index, reg_index)에 해당하는 projection을 그리기
            babyMOSS_projection[(det_index, reg_index)].Draw("COLZ")
            ROOT.gPad.SetRightMargin(0.14)  # Right margin을 조정
            #ROOT.gPad.SetLogy()
        
        # 각 detector별 canvas 저장
        _canvas.SaveAs(f"./fig/projY_babyMOSS_{det_index}_lin.pdf")
        _canvas.Draw()

            


    # 파일 닫기
    root_file.Close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python plot_projection.py <input_root_file>")
        sys.exit(1)

    root_file_path = sys.argv[1]

    ROOT.gStyle.SetOptStat(11)       # 원하는 statbox 옵션 설정 (e.g., 1110: entries, mean, RMS)
    #ROOT.gStyle.SetStatFillStyle(0)        # statbox 배경 투명하게 (0 = 투명)

    plot_projection(root_file_path)
