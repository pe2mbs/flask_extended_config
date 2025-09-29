# -*- coding: utf-8 -*-
#
# Flask Extended Config extension for Flask framework
#
# Copyright (C) 2018-2025 Marc Bertens-Nguyen <m.bertens@pe2mbs.nl>
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License GPL-2.0-only
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import typing as t
import traceback
import platform
import logging
import os
import sys
import errno
import copy
import json
import datetime
from flask import Config as BaseConfig
from mako.template import Template
from mako.exceptions import text_error_template
import io
from flask_extended_config.iterator import lookahead
from flask_extended_config.sqlalchemy_url import SqlalchemyUrl
from flask_extended_config.yaml_load import my_safe_load


__author__ = "Marc Bertens"
__Version__ = "1.0.0"
__all__ = [ 'Config' ]


"""This was original part of the webapp(2) submodules.  
"""


class Config( BaseConfig ):
    """Flask config enhanced with a `from_yaml`, `from_json` and from_folder' methods.

    The from_folder method it loads the configuration from the folder, it assumes a filename 'config.conf'

    General in the configuration there are special sections:

    LOGGING:    This contains the information for the Python log facility, this shall contain the dictionary.

    DATABASE:   This contains the information for the database. With the following sub-keys
        ENGINE:     the sqlalchemy engine name
        DATABASE:   the database name
        SCHEMA:     the schema name for oracle, and for postgresql the search path.
        HOST:       hostname where the database is located
        PORT        the port where the database is located
        USERNAME:   the database username
        PASSWORD:   the password used to authenticate with the database
        OPTIONS:    extra options for the connection

    when 'SQLALCHEMY_DATABASE_URI' is not present in the configuration, 'DATABASE' is used.
    """
    def __init__( self, root_path: str | os.PathLike[str], defaults: t.Optional[ dict[str, t.Any] ] = None,
                  env_name: t.Optional[ str ] = 'FLASK_ENV', task_name: t.Optional[ str ] = 'FLASK_TASK' ) -> None:
        """

        :param root_path:   path to which files are read relative from.  When the
                            config object is created by the application, this is
                            the application's :attr:`~flask.Flask.root_path`.
        :param defaults:    an optional dictionary of default values
        :param env_name:    Environment variable name of the environment section
        :param task_name:   Environment variable name of the tasks section
        """
        super().__init__( root_path, defaults or {} )
        self.__environ_name = env_name
        self.__task_name    = task_name
        return

    def _config_over_ride( self, result: dict, override: dict ) -> dict:
        """Internal function that overrides the keys in 'override' to the dictionary result

        :param result:      source / target dictionary.
        :param override:    holds the keys to be overridden in the source dictionary.
        :return:            the result dictionary.
        """
        for key, value in override.items():
            if isinstance( value, dict ):
                if key not in result:
                    result[ key ] = copy.copy( value )

                else:
                    result[ key ] = self._config_over_ride( result[ key ], value )

            else:
                result[ key ] = value

        return result

    def _config_inject( self, result: dict, folder: str, environ_var: str, target: str, default_section: str ) -> dict:
        """

        :param result:
        :param folder:
        :param environ_var:
        :param target:
        :param default_section:
        :return:
        """
        section_name = os.environ.get( environ_var, default_section )
        if os.path.isdir( folder ):
            configFile = os.path.join( folder, '{}.conf'.format( section_name ) )
            if os.path.isfile( configFile ):
                with open( configFile, 'r' ) as stream:
                    result = self._config_over_ride( result, my_safe_load( stream ) )

            else:
                print( f"No {target} config for {environ_var}", file=sys.stderr)

        else:
            # no custom configurations at all.
            print( f"No 'environ' folder for {section_name} configuration", file=sys.stderr)

        if target == 'ENV':
            result[ 'ENVIRONMENT' ] = section_name

        result[ target ] = section_name
        return result

    def from_folder( self, config_folder: str = None, env_name: t.Optional[ str ] = None,
                     task_name: t.Optional[ str ] = None ) -> bool:
        """First the config/config.yal is loaded as the master configuration.

        Second in sub-folder config/env is checked that a <{FLASK_ENV}>.yaml is located,
        If so it loaded and the attributes from this file are overriding the config.

        Third in sub-folder config/tsk is checked that a <{FLASK_TASK}>.yaml is located,
        If so it loaded and the attributes from this file are overriding the config.

        :param config_folder:
        :param env_name:
        :param task_name:

        :return:
        """
        if isinstance( env_name, str ):
            self.__environ_name = env_name

        if isinstance( task_name, str ):
            self.__task_name = task_name

        if not isinstance( config_folder, str ):
            config_folder = os.path.join( self.root_path, 'config' )

        try:
            if os.path.isdir( config_folder ):
                # Master configuration
                configFile = os.path.join( config_folder, 'config.conf' )
                if os.path.isfile( configFile ):
                    with open( configFile, 'r' ) as stream:
                        result = my_safe_load( stream )

                else:
                    raise Exception( 'No master configuration present {}'.format( configFile ) )

                for key in ( "LOGGING", ):
                    # Check of the item is a string, the file exists and ends with .json or .yaml
                    if isinstance( result[ key ], str ) and result[ key ].lower().endswith( ( '.json', '.conf', '.yaml' ) ):
                        filepath = os.path.abspath( os.path.join( self.root_path, result[ key ] ) )
                        if os.path.exists( filepath ):
                            # This needs to be loaded
                            with open( filepath, 'r' ) as stream:
                                if result[key].lower().endswith('.json' ):
                                    result[ key ] = json.load( stream )

                                else:
                                    result[ key ] = my_safe_load( stream )

                hosts_folder = os.path.join( config_folder, 'hosts', f'{ platform.node() }.conf' )
                if os.path.exists( hosts_folder ):
                    with open(hosts_folder, 'r') as stream:
                        result = self._config_over_ride( result, my_safe_load(stream ) )

                self._config_inject( result, os.path.join( config_folder, 'environ' ),
                                    self.__environ_name, 'ENV', 'DEVELOPMENT' )
                self._config_inject( result, os.path.join( config_folder, 'tasks' ),
                                    self.__task_name, 'TASK', 'webapp' )

            else:
                raise Exception( "Configuration folder not present: {}".format( config_folder ) )

            return self._modify( result )

        except Exception:
            print( traceback.format_exc() )
            raise

    def from_file( self, filename: str | os.PathLike[str],
                         load: t.Callable[[t.IO[t.Any]], t.Mapping[str, t.Any]],
                         silent: bool = False,
                         text: bool = True ) -> dict:
        """Load the configuration from a file, currently JSON and YAML formats
        are supported

        :param filename:        the filename of the JSON or YAML file.
                                This can either be an absolute filename
                                or a filename relative to the root path.
        :param load:
        :param silent:          Ignore the file if it doesn't exist.
        :param text:
        :return:                ``True`` if able to load config,
                                ``False`` otherwise.
        """

        ext = os.path.splitext( filename )[ 1 ]
        if ext == '.json':
            result = self.from_json( filename )

        elif ext in ( '.yml', '.yaml', '.conf' ):
            result = self.from_yaml( filename )

        else:
            raise Exception( f"Could not load file type: '{ ext }'" )

        return result

    def from_yaml( self, config_file: str | os.PathLike[ str ], silent: bool = False ) -> bool:
        """Load the configuration from a file, currently YAML formats
        are supported

        :param config_file:     the filename of the YAML file.
                                This can either be an absolute filename
                                or a filename relative to the root path.
        :param silent:          Ignore the file if it doesn't exist.
        :return:                ``True`` if able to load config,
                                ``False`` otherwise.
        """
        # Get the Flask environment variable, if not exist assume development.
        env = os.environ.get( self.__environ_name, 'DEVELOPMENT' ).upper()
        self[ 'ENVIRONMENT' ] = env.lower()
        try:
            with open( config_file ) as f:
                c = my_safe_load( f )

        except IOError as e:
            if silent and e.errno in ( errno.ENOENT, errno.EISDIR ):
                return False

            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise

        task_section = c.get( 'COMMON_TASKS', {} ).get( os.environ.get( self.__task_name, 'webapp' ), {} )
        return self._modify( c.get( env, c ), task_section )

    def from_json( self, config_file: str | os.PathLike[ str ], silent: bool = False ) -> bool:
        """Load the configuration from a file, currently JSON formats
        are supported

        :param config_file:     the filename of the JSON file.
                                This can either be an absolute filename
                                or a filename relative to the root path.
        :param silent:          Ignore the file if it doesn't exist.
        :return:                ``True`` if able to load config,
                                ``False`` otherwise.
        """

        # Get the Flask environment variable, if not exist assume development.
        env = os.environ.get( self.__environ_name, 'DEVELOPMENT' )
        self[ 'ENVIRONMENT' ] = env.lower()
        try:
            with open( config_file ) as f:
                c = json.load( f )

        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False

            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise

        # Get the environment segment
        segment = copy.copy( c.get( env, c ) )
        # self.__dump( segment )
        if 'inport' in segment:
            # Get the import segment
            c = copy.copy( c.get( segment[ 'inport' ], {} ) )
            # join the selected segment and imported segment, making sure that
            # the selected segment has priority over the imported segment
            c.update( segment )
            segment = c

        if 'COMMON_TASKS' in c:
            task_section = c.get( 'COMMON_TASKS', {} ).get( os.environ.get( self.__task_name, 'webapp' ), {} )

        else:
            task_section = {}

        return self._modify( segment, task_section )

    def _resolve_variables( self, node: dict ) -> None:
        """

        :param node:
        :return:
        """
        for key, value in node.items():
            if isinstance( value, str ):
                if '${' in value:
                    try:
                        node[ key ] = Template( value ).render( **dict( self ) )

                    except:
                        raise Exception( text_error_template().render() )

            elif isinstance( value, dict ):
                self._resolve_variables( value )

        return

    def _modify( self, c, task_section = None ) -> bool:
        """Internal updater to fix PATH's and DATABASE uri

        :param c:
        :param task_section:
        :return:
        """
        delta_keys = ( "PERMANENT_SESSION_LIFETIME",
                       "SEND_FILE_MAX_AGE_DEFAULT",
                       "JWT_ACCESS_TOKEN_EXPIRES",
                       "JWT_REFRESH_TOKEN_EXPIRES" )

        if isinstance( task_section, dict ):
            def resolve_keys( path, keys, value ):
                for key, more in lookahead( keys ):
                    if more:
                        path = path[ key ]

                    else:
                        path[ key ] = value
                        return

                return

            def resolve_key( path, upd ):
                for key, value in  upd.items():
                    if '.' in key:
                        resolve_keys( c, key.split( '.' ), value )

                    elif isinstance( value, dict ):
                        if key in path:
                            path[ key ] = resolve_key( path[ key ], value )

                        else:
                            path[ key ] = value

                    else:
                        path[ key ] = value

                return path

            try:
                resolve_key( c, task_section )

            except Exception:
                logging.getLogger().exception( "Resolving the config failed" )
                raise

        for key in c.keys():
            if key.isupper():
                # Is the variable '**PATH**' in the name and starts with a dot.
                if "PATH" in key and c[ key ].startswith( '.' ):
                    # Resolve the path to a full path
                    self[ key ] = os.path.abspath( os.path.join( self.root_path, c[ key ] ) )

                else:
                    def func( value ):
                        try:
                            return int( value )

                        except Exception as exc:        # noqa
                            pass

                        return value

                    if key in delta_keys:
                        if '=' in c[ key ]:
                            # convert the string to a dict.
                            settings = dict( map( func, x.split( '=' ) ) for x in c[ key ].split( ',' ) )
                            self[ key ] = datetime.timedelta( **settings )

                        else:
                            self[ key ] = c[ key ]

                    else:
                        self[ key ] = c[ key ]

        self._resolve_variables( self )
        if 'DATABASE' in self and 'SQLALCHEMY_DATABASE_URI' not in self:
            self[ 'SQLALCHEMY_DATABASE_URI' ] = SqlalchemyUrl.from_config_dict( self[ 'DATABASE' ] )

        self.dump()
        return True

    def dump( self ) -> None:
        if os.environ.get( 'FLASK_DEBUG', 0 ) == 0 and self.get( 'DEBUG', 0 ) == 0:
            return

        logger = logging.getLogger( 'webapp' )
        logger.setLevel( "INFO" )
        with io.StringIO() as stream:
            self._dumper( dict( self ), stream )
            stream.seek( 0, 0 )
            if stream:
                print( f"Configuration:\n{ stream.getvalue() } " )

            else:
                logger.info( f"Configuration:\n{ stream.getvalue() } " )

        return

    @property
    def struct( self ) -> dict:
        return dict( self )

    def _dumper( self, node: t.Union[ dict, list ], stream: io.IOBase, indent: int = 0, prefix: str = '', value_column: int = 35 ) -> None:
        if isinstance( node, dict ):
            indent_str = ' ' * indent
            offset = value_column - indent
            for key, value in node.items():
                if isinstance( value, dict ):
                    stream.write( f"{indent_str}{key:{offset}s} :\n" )
                    self._dumper( value, stream, indent + 4 )

                elif isinstance( value, list ):
                    stream.write( f"{indent_str}{key:{offset}s} :\n" )
                    self._dumper( value, stream, indent + 4, prefix= '-' )

                else:
                    stream.write( f"{indent_str}{ prefix }{key:{offset}s} : { str( value ) }\n" )

        return
