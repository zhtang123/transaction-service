from django.db import models

class ScheduledUserOp(models.Model):
    userophash = models.CharField(max_length=255, primary_key=True)
    status = models.CharField(max_length=255)
    time = models.DateTimeField()
    task_id = models.CharField(max_length=255)

    class Meta:
        db_table = 'scheduled_userop'


class UserOperationHash(models.Model):
    userophash = models.CharField(max_length=255, primary_key=True)
    transactionhash = models.CharField(max_length=255)

    class Meta:
        db_table = 'userop_txn'

class TransactionStatus(models.Model):
    transactionhash = models.CharField(max_length=255, primary_key=True)
    status = models.CharField(max_length=50)

    class Meta:
        db_table = 'txn_status'