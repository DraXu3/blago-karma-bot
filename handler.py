import asyncio
import json
import logging

from main import init

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

loop = asyncio.get_event_loop()

def webhook(event, _):
    try:
        logger.info(event)
        update = json.loads(event["body"])

        bot_manager = init()
        loop.run_until_complete(bot_manager.process_update(update))

        return { "statusCode": 200 }
                
    except Exception as e:
        logger.error(e)

        return { "statusCode": 500 }

