import os
import requests
import logging
import json

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import UserOperationHash, TransactionStatus

@csrf_exempt
@transaction.atomic
def get_transaction_status(request):
    data = json.loads(request.body)
    chain = data.get('chain')
    userophash = data.get('userophash')

    try:
        user_operation = UserOperationHash.objects.get(userophash=userophash)
        transactionhash = user_operation.transactionhash

        try:
            transaction_status = TransactionStatus.objects.select_for_update().get(transactionhash=transactionhash)
        except TransactionStatus.DoesNotExist:
            transaction_status = TransactionStatus(transactionhash=transactionhash, status='pending')
            transaction_status.save()

        return JsonResponse({'status': transaction_status.status, 'transactionhash': transactionhash})

    except UserOperationHash.DoesNotExist:
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

        transaction_status = TransactionStatus(transactionhash=transactionhash, status=('pending' if success is True else 'failed'))
        transaction_status.save()

        return JsonResponse({'status': transaction_status.status, 'transactionhash': transactionhash})
