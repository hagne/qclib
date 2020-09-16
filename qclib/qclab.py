# -*- coding: utf-8 -*-
import qclib.tag_times


def qc_by_tagging_times(path2data, path2database):
    out = qclib.tag_times.Controller(path2data=path2data, path2database=path2database)
    return out
    