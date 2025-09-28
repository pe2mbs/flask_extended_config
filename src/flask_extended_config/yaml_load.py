import yaml
import os.path


def my_compose_document( self ):
    """

    :param self:
    :return:
    """
    self.get_event()
    node = self.compose_node(None, None)
    self.get_event()
    # self.anchors = {}    # <<<< commented out
    return node


yaml.SafeLoader.compose_document = my_compose_document


def yaml_include( loader, node ):
    """

    :param loader:
    :param node:
    :return:
    """
    if node.value.startswith( '.' ):
        include_name = os.path.join( os.path.dirname( node.start_mark.name ), node.value )

    else:
        include_name = node.value

    include_name = os.path.abspath( include_name )
    with open( include_name, 'r' ) as input_file:
        data = my_safe_load( input_file, master = loader )
        return data


yaml.add_constructor( "!include", yaml_include, Loader = yaml.SafeLoader )


def my_safe_load( stream, Loader = yaml.SafeLoader, master = None ) -> dict:            # noqa
    """

    :param stream:
    :param Loader:
    :param master:
    :return:
    """
    loader = Loader( stream )
    if master is not None:
        loader.anchors = master.anchors

    try:
        return loader.get_single_data()

    finally:
        loader.dispose()
