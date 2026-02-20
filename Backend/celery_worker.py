from celery import Celery
 
def make_celery(app=None):


    print("make_celery  ...  app  ",app)
 
    celery = Celery(
        app.import_name if app else "tasks",
        broker="redis://172.17.128.1:6379/0",
        backend="redis://172.17.128.1:6379/0"
    )
 
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
 
    if app:
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
 
        celery.Task = ContextTask
 
    return celery