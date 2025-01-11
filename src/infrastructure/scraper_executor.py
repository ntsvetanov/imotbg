from concurrent.futures import ThreadPoolExecutor, as_completed

from src.logger_setup import get_logger

logger = get_logger(__name__)

from concurrent.futures import TimeoutError

from src.logger_setup import get_logger

logger = get_logger(__name__)


class ScraperExecutor:
    def __init__(self, timeout, max_workers=10):
        self.timeout = timeout
        self.max_workers = max_workers
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        if not callable(func):
            raise ValueError(f"Task must be a callable. Received: {func}")
        self.tasks.append((func, args, kwargs))

    def run(self, exception_handler=None):
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(func, *args, **kwargs): (func, args, kwargs) for func, args, kwargs in self.tasks
            }

            try:
                for future in as_completed(future_to_task, timeout=self.timeout):
                    func, args, kwargs = future_to_task[future]
                    try:
                        result = future.result()
                        logger.info(f"Task {func.__name__} completed with result type: {type(result)}")
                        results.append(result)
                    except Exception as e:
                        logger.error(
                            f"Error in task {func.__name__} with args {args} and kwargs {kwargs}: {e}", exc_info=True
                        )
                        if exception_handler:
                            exception_handler(func, args, kwargs, e)
            except TimeoutError:
                logger.error("Timeout occurred while waiting for tasks to complete.", exc_info=True)
                for future in future_to_task.keys():
                    future.cancel()
            except Exception as e:
                logger.critical(f"Critical error during task execution: {e}. Cancelling all tasks.", exc_info=True)
                for future in future_to_task.keys():
                    future.cancel()
        logger.info(f"All tasks completed. Results collected: {len(results)}")
        return results
