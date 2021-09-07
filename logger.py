"""Custom Logger Module"""

import logging


from inspect import stack
from logging import Filter, Formatter, StreamHandler
from logging.handlers import TimedRotatingFileHandler
from os import makedirs, sep
from os.path import abspath, exists, split, splitext
from pathlib import Path


level = logging.INFO
loggers = {}
log_dir = str(Path(__file__).resolve().parent / 'logs')


def get_logger(logger_name=None, func_name=None, funcname=True, level=level, mini=False):
    global loggers
    stck = stack()
    src_fyl = stck[1][1]
    func_name = func_name if func_name else splitext(src_fyl.split(sep)[-1])[0]
    if loggers.get(logger_name):
        return loggers.get(logger_name)
    else:
        logger_name = stack()[1][3].replace('<', '').replace('>', '') if not logger_name else logger_name
        l = logging.getLogger(logger_name)
        l.propagate = False
        # formatter = logging.Formatter('%(asctime)s : %(message)s')     %(os.getpid())s|

        if mini:
            formatter = Formatter('%(message)s')
        else:
            formatter = Formatter(
                # '%(processName)s : %(process)s | %(threadName)s : %(thread)s:\n'
                '%(process)s - %(thread)s @ '
                '%(asctime)s {%(name)s:%(lineno)d  - %(funcName)18s()} %(levelname)s - %(message)s')
        # '[%(asctime)s] - {%(name)s:%(lineno)d  - %(funcName)20s()} - %(levelname)s - %(message)s')
        # fileHandler = TimedRotatingFileHandler(log_dir + '%s.log' % logger_name, mode='a')
        log_dir2use = log_dir + sep  # + logger_name + sep
        if not exists(log_dir2use):
            makedirs(log_dir2use)
        if l.handlers:
            l.handlers = []
        fileHandler = TimedRotatingFileHandler(log_dir2use + '%s.log' % logger_name)
        fileHandler.setFormatter(formatter)
        streamHandler = StreamHandler()
        streamHandler.setFormatter(formatter)

        l.setLevel(level)
        l.addHandler(fileHandler)
        l.addHandler(streamHandler)
        loggers.update(dict(name=logger_name))

        return l
