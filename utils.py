import logging


def get_logger(name, log_file, level = logging.INFO):
    formatter = logging.Formatter(f'%(module)s - %(funcName)s: %(message)s')

    handler = logging.FileHandler(f"logs/{log_file}", mode='w')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    

    return logger
