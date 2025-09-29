from sqlalchemy import URL


class SqlalchemyUrl( URL ):
    @classmethod
    def from_config_dict( cls, data: dict ):
        """

        :param data:
        :return:
        """
        engine = data[ 'ENGINE' ]
        settings = { 'drivername': engine }
        if engine == 'sqlite':
            # For Sqlite the connect string is different, contains path and database filename
            settings[ 'database' ] = data[ 'DATABASE' ]

        elif engine == 'oracle' and 'SCHEMA' in data and 'HOST' not in data:
            settings[ 'schema' ] = data[ 'SCHEMA' ]

        else:
            settings[ 'database' ] = data['DATABASE' ]
            if 'HOST' not in data:
                settings['host'] = 'localhost'

            else:
                # 'HOST_ADDRESS' set to 'HOST' and 'PORT' variable
                settings[ 'host' ] = data[ 'HOST' ]
                settings[ 'port' ] = data[ 'PORT' ]

            if 'USERNAME' in data:
                # Include username and password into the 'HOST_ADDRESS'
                settings[ 'username' ] = data[ 'USERNAME' ]

            if 'PASSWORD' in data:
                settings[ 'password' ] = data[ 'PASSWORD' ]

        if 'OPTIONS' in data:
            # Adding special options to the connection
            settings[ 'query' ] = data[ 'OPTIONS' ]

        if engine.startswith( 'postgresql' ) and 'SCHEMA' in data:
            settings.setdefault( 'query', {} )[ 'options' ] = '-c search_path={SCHEMA}'.format( **data )

        return cls.create( **settings )
