"""   Control the logging for the application.   """

import logging


class AppLogger:
    """
    A class for logging. Intended to be used as dependency injection.

    Implemented as a singleton.

    """
    __instance = None
    __name = "AppLogger"

    def __init__(self) -> None:
        raise RuntimeError(f"Do not Instantiate {__class__.__name__}, call init_logger()")

    @classmethod
    def init_logger(cls):
        """ Initialize the logger singleton  """
        if cls.__instance is None:
            cls.__instance = cls.__new__(cls)
            cls.__instance = logging.getLogger(__class__.__name__)

        return cls.__instance
    
    @property
    def name(self):
        return self.__name


if __name__ == "__main__":

    log1 = AppLogger.init_logger()
    print(log1, log1.name)

    log2 = AppLogger.init_logger()
    print(log2, log2.name)

    print(f"Loggers the same instance? {log1 is log2}")