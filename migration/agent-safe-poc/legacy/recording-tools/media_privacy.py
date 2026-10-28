"""Map declared privacy intervals from actual source times to display frames.

Original recordings remain unchanged. No mask is inferred from model text.
"""
from copy import deepcopy


def review_overrides(overrides):
    return {group:dict(privacyMasks=deepcopy(overrides[group]['privacyMasks']))
            for group in ('bare','protected') if overrides.get(group,{}).get('privacyMasks')}


def mask_runs(sample_times,masks,width,height):
    result=[]
    for mask in masks:
        start,end=mask['startUnixMs'],mask['endUnixMs']
        x,y,w,h=mask['rect']
        if start>end or min(x,y)<0 or min(w,h)<=0 or x+w>width or y+h>height:
            raise ValueError('Invalid source privacy interval or rectangle')
        active=None
        for index,timestamp in enumerate(sample_times):
            hit=start<=timestamp<=end
            if hit and active is None:active=index
            if active is not None and (not hit or index==len(sample_times)-1):
                result.append(dict(firstFrame=active,lastFrame=index if hit else index-1,rect=[x,y,w,h]))
                active=None
    return result


def ffmpeg_filters(runs):
    filters=[]
    for run in runs:
        x,y,w,h=run['rect']
        enabled=f"between(n,{run['firstFrame']},{run['lastFrame']})"
        font_size=min(32,max(1,w//14),max(1,h//3))
        filters.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0xe5e7eb:t=fill:enable='{enabled}'")
        filters.append("drawtext=fontfile='C\\:/Windows/Fonts/msyh.ttc':text='无关聊天区域已遮挡':"
            f"x={x}+({w}-tw)/2:y={y}+({h}-th)/2:fontsize={font_size}:fontcolor=0x334155:enable='{enabled}'")
    return filters
