import logging

_logger_initialized = False


def get_logger(name: str) -> logging.Logger:
    global _logger_initialized
    logger = logging.getLogger(name)

    if not _logger_initialized:
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        logging.getLogger().addHandler(console_handler)
        logging.getLogger().setLevel(logging.INFO)
        _logger_initialized = True

    return logger
