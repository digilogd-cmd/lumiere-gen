# -*- coding: utf-8 -*-
"""뤼미에르 젠의 파트·단계 순서. 단계 폴더 = work/<프로젝트>/gen_NN_<단계>(예: gen_03_board).
(촬영본 편집 파트 — 롱폼·쇼츠·썸네일 — 는 뤼미에르 에디트에만 있음, 2026-10-09 분리 정리)"""

PARTS = {
    # 생성형(2026-10-08): 주제·대본 -> 대본·콘티 -> [브라우저] 그림·영상·목소리·음악 -> 조립·종편·썸네일. 단계 코드는 stages/gen_*.py
    "gen": {"label": "생성형 제작", "prefix": "gen",
            "order": ["gen_brief", "gen_script", "gen_board", "gen_images", "gen_storyboard", "gen_video", "gen_voice", "gen_align",
                      "gen_music", "gen_assemble", "gen_final", "gen_thumbs", "gen_report"]},
}


def part_of(name):
    for k, p in PARTS.items():
        if name in p["order"]:
            return k
    raise KeyError(name)


def dir_name(name):
    k = part_of(name)
    p = PARTS[k]
    short = name[4:] if k == "gen" else name          # gen_03_board (gen_03_gen_board 가 아니라)
    return f"{p['prefix']}_{p['order'].index(name) + 1:02d}_{short}"
