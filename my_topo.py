from mininet.topo import Topo

class Lab4Topo( Topo ):
    def __init__( self ):
        Topo.__init__( self )
  
        s1 = self.addSwitch( 's1' )
  
topos = { 'topo': ( lambda: Lab4Topo() ) }

