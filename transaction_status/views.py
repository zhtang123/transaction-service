import os
import requests
import logging
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import UserOperationHash, TransactionStatus, ScheduledUserOp, ModifiedUserOp

@csrf_exempt
def get_transaction_status(request):
    data = json.loads(request.body)
    chain = data.get('chain')
    original_userophash = data.get('userophash')
    new_userophash = None

    # Check for modified userop hash
    modified_userop = ModifiedUserOp.objects.filter(old_userophash=original_userophash).first()
    if modified_userop is not None:
        new_userophash = modified_userop.new_userophash

    try:
        user_operation = UserOperationHash.objects.get(userophash=new_userophash if new_userophash else original_userophash)
        transactionhash = user_operation.transactionhash

        transaction_status, created = TransactionStatus.objects.get_or_create(
            transactionhash=transactionhash,
            defaults={'status': 'pending'}
        )

        response_data = {'status': transaction_status.status, 'transactionhash': transactionhash}
        if new_userophash:
            response_data['new_userophash'] = new_userophash

        return JsonResponse(response_data)

    except UserOperationHash.DoesNotExist:
        try:
            schedule_status = ScheduledUserOp.objects.get(userophash=new_userophash if new_userophash else original_userophash)
            if not schedule_status.status == 'completed':
                response_data = {'status': schedule_status.status}
                if new_userophash:
                    response_data['new_userophash'] = new_userophash

                return JsonResponse(response_data)
        except:
            pass

        logging.warning({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getUserOperationByHash",
            "params": [new_userophash if new_userophash else original_userophash]
        })
        logging.warning(f'{os.environ["BUNDLER_URL"]}/{chain}')
        response = requests.post(f'{os.environ["BUNDLER_URL"]}/{chain}',
                                json={
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "eth_getUserOperationReceipt",
                                    "params": [new_userophash if new_userophash else original_userophash]
                                })
        response_json = response.json()
        logging.warning(response_json)

        if 'error' in response_json:
            response_data = {'status': "pending"}
            if new_userophash:
                response_data['new_userophash'] = new_userophash
            return JsonResponse(response_data)

        transactionhash = response_json['result']['logs'][0]['transactionHash']
        success = response_json['result']['success']
        user_operation = UserOperationHash(userophash=new_userophash if new_userophash else original_userophash, transactionhash=transactionhash)
        user_operation.save()

        logging.error(('pending' if success == "true" else 'failed'))

        transaction_status, created = TransactionStatus.objects.get_or_create(
            transactionhash=transactionhash,
            defaults={'status': ('pending' if success is True else 'failed')}
        )

        response_data = {'status': transaction_status.status, 'transactionhash': transactionhash}
        if new_userophash:
            response_data['new_userophash'] = new_userophash

        return JsonResponse(response_data)

