from concurrent.futures import ThreadPoolExecutor, as_completed


class ScraperExecutor:
    def __init__(self, timeout):
        self.timeout = timeout
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))

    def run(self):
        results = []
        with ThreadPoolExecutor() as executor:
            future_to_task = {
                executor.submit(func, *args, **kwargs): (func, args, kwargs) for func, args, kwargs in self.tasks
            }

            for future in as_completed(future_to_task):
                func, args, kwargs = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Error in task {func.__name__}: {e}")
        return results
