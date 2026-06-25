import asyncio
from database import connect_to_mongo, db_instance

async def test():
    await connect_to_mongo()
    s = await db_instance.inspection_sessions.find_one({'session_id': 'b53041a2-f93f-4b2f-8fbe-25ed5299b669'})
    if s:
        print('PROGRESS IS', s.get('progress'))
        print('STATUS IS', s.get('status'))
        print('CURRENT_STAGE IS', s.get('current_stage'))
        print('FAILED_STAGE IS', s.get('failed_stage'))
        print('ERROR_MESSAGE IS', s.get('error_message'))
    else:
        print('NO SESSION FOUND')

asyncio.run(test())
