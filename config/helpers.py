import logging

def qdebug(*args, sep: str = " ", end: str = ""):
    message = sep.join([str(arg) for arg in args])
    logging.debug(message)

def qwarning(*args, sep: str = " ", end: str = ""):
    message = sep.join([str(arg) for arg in args])
    logging.warning(message)