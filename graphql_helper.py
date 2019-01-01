import logging
import traceback
import json
from graphqlclient import GraphQLClient
from config import constants

class GraphQLHelper:

    def __init__(self):
        self.client = GraphQLClient(constants["GRAHQL_CLIENT_URL"])
        self.client.inject_token(constants["GRAPHQL_TOKEN"], 'X-Hasura-Access-Key')

    def upsert(self, table, data, return_column):
        query = '''
        mutation upsert_{TABLE_NAME}($objects: [{TABLE_NAME}_insert_input!]! ) {{
          insert_{TABLE_NAME}(objects: $objects,
            on_conflict: {{
              constraint: {TABLE_NAME}_pkey
            }}
          ) {{
            affected_rows
            returning{{
              {KEY}
            }}
          }}
        }}
        '''
        query = query.format(TABLE_NAME=table, KEY=return_column)
        try:
            return self.client.execute(query, {"objects": data})
        except Exception as e:
            logging.info(traceback.format_exc())
            raise e

    def update(self, table, equals_obj="{}", set_obj="{}", inc_obj="{}", return_column="{}"):
        query = '''
            mutation update_{TABLE_NAME} {{
                update_{TABLE_NAME}(
                    where: {EQUALS_OBJ},
                    _set: {SET_OBJ}
                    _inc: {INC_OBJ}
                )   {{
                    affected_rows
                    returning {{
                        {RETURN_COLUMN}
                    }}
                }}
            }}
        '''
        query = query.format(TABLE_NAME=table, EQUALS_OBJ=equals_obj, SET_OBJ=set_obj, INC_OBJ= inc_obj, RETURN_COLUMN=return_column)
        try:
            return json.loads(self.client.execute(query))['data']['update_' + table]['returning']
        except Exception as e:
            logging.info(traceback.format_exc())
            raise e

    def select(self, table, where_obj, order_by_obj, return_column):
        query = '''
            query
            {{
                {TABLE_NAME}(
                    where: {WHERE_OBJ} 
                    order_by: {ORDER_BY_OBJ}
                ){{
                    {RETURN_COLUMN}  
                }}
            }}
        '''
        query = query.format(TABLE_NAME=table, WHERE_OBJ=where_obj, ORDER_BY_OBJ=order_by_obj, RETURN_COLUMN=return_column)
        try:
            return json.loads(self.client.execute(query))
        except Exception as e:
            logging.info(traceback.format_exc())
            raise e



