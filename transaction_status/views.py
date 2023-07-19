import os
import requests
import logging
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import UserOperationHash, TransactionStatus, ScheduledUserOp

@csrf_exempt
def get_transaction_status(request):
    data = json.loads(request.body)
    chain = data.get('chain')
    userophash = data.get('userophash')

    try:
        user_operation = UserOperationHash.objects.get(userophash=userophash)
        transactionhash = user_operation.transactionhash

        transaction_status, created = TransactionStatus.objects.get_or_create(
            transactionhash=transactionhash,
            defaults={'status': 'pending'}
        )

        return JsonResponse({'status': transaction_status.status, 'transactionhash': transactionhash})

    except UserOperationHash.DoesNotExist:
        try:
            schedule_status = ScheduledUserOp.objects.get(userophash=userophash)
            if schedule_status.status is not 'completed':
                return JsonResponse({'status': schedule_status.status})
        except:
            pass
        logging.warning({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getUserOperationByHash",
            "params": [userophash]
        })
        logging.warning(f'{os.environ["BUNDLER_URL"]}/{chain}')
        response = requests.post(f'{os.environ["BUNDLER_URL"]}/{chain}',
                                json={
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "eth_getUserOperationReceipt",
                                    "params": [userophash]
                                })
        response_json = response.json()
        logging.warning(response_json)

        if 'error' in response_json:
            return JsonResponse({'status': "pending"})

        transactionhash = response_json['result']['logs'][0]['transactionHash']
        success = response_json['result']['success']
        user_operation = UserOperationHash(userophash=userophash, transactionhash=transactionhash)
        user_operation.save()

        logging.error(('pending' if success == "true" else 'failed'))

        transaction_status, created = TransactionStatus.objects.get_or_create(
            transactionhash=transactionhash,
            defaults={'status': ('pending' if success is True else 'failed')}
        )

        return JsonResponse({'status': transaction_status.status, 'transactionhash': transactionhash})
