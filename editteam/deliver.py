# -*- coding: utf-8 -*-
"""완성본 모으기: work/<프로젝트>/완성/ 한 곳에 사용자가 쓸 파일만(이름을 알아보기 쉽게). 같은 드라이브면 하드링크(용량 0), 아니면 복사.
runner 가 끝날 때, 대시보드 [📁 완성 폴더]가 부른다. 무엇을 모을지는 gen/deliver.collect_gen."""
import os, shutil


def _put(src, dst):
    if not src or not os.path.isfile(src):
        return None
    if os.path.exists(dst):
        try:
            if os.path.samefile(src, dst):
                return dst
        except OSError:
            pass
        try:
            os.remove(dst)
        except OSError:
            return dst            # 재생기에 열려 있으면 그대로 둔다
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
    return dst



def collect(P):
    from .gen.deliver import collect_gen
    return collect_gen(P)
