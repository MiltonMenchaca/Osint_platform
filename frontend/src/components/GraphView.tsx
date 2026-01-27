import React, { useEffect, useRef, useState, useCallback } from 'react';

import cytoscape from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import {
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,

  Download,
  Shuffle,
  X,
  User,
  Building2,
  Mail,
  Phone,
  MapPin,
  Globe,

  CreditCard,
  Calculator,

  Calendar,
  Clock,
  Briefcase,
  Users,
  Server,
  Shield,
  Wifi,
  Smartphone,
  Home,
  Building,
  Flag,
  Hash,
  Navigation
} from 'lucide-react';

// Registrar el layout
cytoscape.use(coseBilkent);

import type { GraphNode, GraphEdge } from '../types';

interface GraphViewProps {
  investigationData?: {
    nodes?: GraphNode[];
    edges?: GraphEdge[];
  };
  nodes?: GraphNode[];
  edges?: GraphEdge[];
  onNodeSelect?: (node: GraphNode | null) => void;
}

const GraphView: React.FC<GraphViewProps> = ({ investigationData, nodes: propNodes, edges: propEdges, onNodeSelect }) => {
  // Datos mock para cuando no hay datos reales
  const mockNodes: GraphNode[] = [
    {
      id: '1',
      type: 'person',
      data: {
        name: 'Juan Pérez',
        birthDate: '1985-03-15',
        birthPlace: 'Ciudad de México',
        gender: 'M'
      }
    },
    {
      id: '2',
      type: 'company',
      data: {
        businessName: 'Tech Solutions SA',
        foundedDate: '2010-06-20'
      }
    },
    {
      id: '3',
      type: 'email',
      data: {
        email: 'juan.perez@techsolutions.com'
      }
    },
    {
      id: '4',
      type: 'phone',
      data: {
        number: '+52 55 1234 5678'
      }
    },
    {
      id: '5',
      type: 'domain',
      data: {
        domain: 'techsolutions.com'
      }
    }
  ];

  const mockEdges: GraphEdge[] = [
    {
      id: 'e1',
      source: '1',
      target: '2',
      type: 'works_at',
      data: { relationship: 'Empleado' }
    },
    {
      id: 'e2',
      source: '1',
      target: '3',
      type: 'owns',
      data: { relationship: 'Propietario' }
    },
    {
      id: 'e3',
      source: '1',
      target: '4',
      type: 'owns',
      data: { relationship: 'Propietario' }
    },
    {
      id: 'e4',
      source: '2',
      target: '5',
      type: 'owns',
      data: { relationship: 'Dominio corporativo' }
    }
  ];

  // Extraer nodes y edges de investigationData o usar props directamente, o usar mock data
  const nodes = propNodes || investigationData?.nodes || mockNodes;
  const edges = propEdges || investigationData?.edges || mockEdges;
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInstance = useRef<cytoscape.Core | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Función para calcular CURP
  const calculateCURP = (data: any) => {
    if (!data.name || !data.birthDate || !data.birthPlace || !data.gender) return 'N/A';
    
    const names = data.name.split(' ');
    const firstName = names[0] || '';
    const lastName1 = names[1] || '';
    const lastName2 = names[2] || '';
    
    const birthYear = new Date(data.birthDate).getFullYear().toString().slice(-2);
    const birthMonth = String(new Date(data.birthDate).getMonth() + 1).padStart(2, '0');
    const birthDay = String(new Date(data.birthDate).getDate()).padStart(2, '0');
    
    const curp = `${lastName1.charAt(0)}${getFirstVowel(lastName1)}${lastName2.charAt(0)}${firstName.charAt(0)}${birthYear}${birthMonth}${birthDay}${data.gender}${getStateCode(data.birthPlace)}${getFirstConsonant(lastName1)}${getFirstConsonant(lastName2)}${getFirstConsonant(firstName)}XX`;
    
    return curp.toUpperCase();
  };

  // Función para calcular RFC
  const calculateRFC = (data: any) => {
    if (!data.businessName || !data.foundedDate) return 'N/A';
    
    const words = data.businessName.split(' ').filter((word: string) => word.length > 0);
    let rfc = '';
    
    if (words.length >= 3) {
      rfc = words[0].charAt(0) + words[1].charAt(0) + words[2].charAt(0);
    } else if (words.length === 2) {
      rfc = words[0].charAt(0) + words[1].charAt(0) + words[1].charAt(1);
    } else {
      rfc = words[0].substring(0, 3);
    }
    
    const foundedYear = new Date(data.foundedDate).getFullYear().toString().slice(-2);
    const foundedMonth = String(new Date(data.foundedDate).getMonth() + 1).padStart(2, '0');
    const foundedDay = String(new Date(data.foundedDate).getDate()).padStart(2, '0');
    
    return `${rfc}${foundedYear}${foundedMonth}${foundedDay}XXX`.toUpperCase();
  };

  const getFirstVowel = (str: string) => {
    const vowels = 'AEIOU';
    for (let i = 1; i < str.length; i++) {
      if (vowels.includes(str[i].toUpperCase())) {
        return str[i].toUpperCase();
      }
    }
    return 'X';
  };

  const getFirstConsonant = (str: string) => {
    const vowels = 'AEIOU';
    for (let i = 1; i < str.length; i++) {
      if (!vowels.includes(str[i].toUpperCase()) && str[i].match(/[A-Z]/i)) {
        return str[i].toUpperCase();
      }
    }
    return 'X';
  };

  const getStateCode = (state: string) => {
    const stateCodes: { [key: string]: string } = {
      'Aguascalientes': 'AS',
      'Baja California': 'BC',
      'Baja California Sur': 'BS',
      'Campeche': 'CC',
      'Chiapas': 'CS',
      'Chihuahua': 'CH',
      'Ciudad de México': 'DF',
      'Coahuila': 'CL',
      'Colima': 'CM',
      'Durango': 'DG',
      'Estado de México': 'MC',
      'Guanajuato': 'GT',
      'Guerrero': 'GR',
      'Hidalgo': 'HG',
      'Jalisco': 'JC',
      'Michoacán': 'MN',
      'Morelos': 'MS',
      'Nayarit': 'NT',
      'Nuevo León': 'NL',
      'Oaxaca': 'OC',
      'Puebla': 'PL',
      'Querétaro': 'QT',
      'Quintana Roo': 'QR',
      'San Luis Potosí': 'SP',
      'Sinaloa': 'SL',
      'Sonora': 'SR',
      'Tabasco': 'TC',
      'Tamaulipas': 'TS',
      'Tlaxcala': 'TL',
      'Veracruz': 'VZ',
      'Yucatán': 'YN',
      'Zacatecas': 'ZS'
    };
    return stateCodes[state] || 'NE';
  };

  // Configuración de colores y estilos mejorados
  const getNodeStyle = (type: string) => {
    const baseStyle = {
      'width': 80,
      'height': 80,
      'shape': 'round-rectangle', // Nodos cuadrados con bordes redondeados
      'border-width': 3,
      'border-opacity': 1,
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 5,
      'font-size': '12px',
      'font-weight': '600',
      'text-wrap': 'wrap',
      'text-max-width': '80px',
      'overlay-opacity': 0
    };

    const typeStyles: { [key: string]: any } = {
      person: {
        ...baseStyle,
        'background-color': '#3498db',
        'border-color': '#2980b9',
        'color': '#ffffff'
      },
      company: {
        ...baseStyle,
        'background-color': '#9b59b6',
        'border-color': '#8e44ad',
        'color': '#ffffff'
      },
      email: {
        ...baseStyle,
        'background-color': '#27ae60',
        'border-color': '#229954',
        'color': '#ffffff'
      },
      phone: {
        ...baseStyle,
        'background-color': '#e74c3c',
        'border-color': '#c0392b',
        'color': '#ffffff'
      },
      address: {
        ...baseStyle,
        'background-color': '#f39c12',
        'border-color': '#e67e22',
        'color': '#ffffff'
      },
      domain: {
        ...baseStyle,
        'background-color': '#1abc9c',
        'border-color': '#16a085',
        'color': '#ffffff'
      }
    };

    return typeStyles[type] || typeStyles.person;
  };

  const getNodeIcon = (type: string) => {
    const icons: { [key: string]: string } = {
      person: '👤',
      company: '🏢',
      email: '📧',
      phone: '📞',
      address: '📍',
      domain: '🌐'
    };
    return icons[type] || '❓';
  };

  const initializeGraph = useCallback(() => {
    if (!cyRef.current) return;

    // Limpiar instancia anterior
    if (cyInstance.current) {
      cyInstance.current.destroy();
    }

    // Crear elementos para Cytoscape
    const elements = [
      ...nodes.map(node => ({
        data: {
          id: node.id,
          label: `${getNodeIcon(node.type)}\n${node.data.name || node.data.email || node.data.number || node.data.domain || node.id}`,
          type: node.type,
          nodeData: node.data
        }
      })),
      ...edges.map(edge => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: edge.type
        }
      }))
    ];

    // Inicializar Cytoscape
    cyInstance.current = cytoscape({
      container: cyRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: getNodeStyle('person')
        },
        ...['person', 'company', 'email', 'phone', 'address', 'domain'].map(type => ({
          selector: `node[type = "${type}"]`,
          style: getNodeStyle(type)
        })),
        {
          selector: 'edge',
          style: {
            'width': 3,
            'line-color': '#95a5a6',
            'target-arrow-color': '#95a5a6',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1.2,
            'opacity': 0.8
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 4,
            'border-color': '#f1c40f',
            'overlay-opacity': 0.2,
            'overlay-color': '#f1c40f'
          }
        },
        {
          selector: '.highlighted',
          style: {
            'background-color': '#f1c40f',
            'border-color': '#f39c12',
            'line-color': '#f1c40f',
            'target-arrow-color': '#f1c40f',
            'opacity': 1
          }
        },
        {
          selector: '.dimmed',
          style: {
            'opacity': 0.3
          }
        }
      ],
      layout: {
        name: 'cose-bilkent'
      },
      wheelSensitivity: 0.2,
      minZoom: 0.3,
      maxZoom: 3
    });

    // Event listeners
    cyInstance.current.on('tap', 'node', (evt) => {
      const node = evt.target;
      const nodeData = {
        id: node.id(),
        type: node.data('type'),
        data: node.data('nodeData')
      };
      setSelectedNode(nodeData);
      setSidebarOpen(true);
      onNodeSelect?.(nodeData);
    });

    cyInstance.current.on('tap', (evt) => {
      if (evt.target === cyInstance.current) {
        setSelectedNode(null);
        setSidebarOpen(false);
        onNodeSelect?.(null);
      }
    });

    // Highlight connected nodes on hover
    cyInstance.current.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      const connectedEdges = node.connectedEdges();
      const connectedNodes = connectedEdges.connectedNodes();
      
      cyInstance.current?.elements().addClass('dimmed');
      node.removeClass('dimmed').addClass('highlighted');
      connectedNodes.removeClass('dimmed').addClass('highlighted');
      connectedEdges.removeClass('dimmed').addClass('highlighted');
    });

    cyInstance.current.on('mouseout', 'node', () => {
      cyInstance.current?.elements().removeClass('dimmed highlighted');
    });

  }, [nodes, edges, onNodeSelect]);

  useEffect(() => {
    initializeGraph();
    
    return () => {
      if (cyInstance.current) {
        cyInstance.current.destroy();
      }
    };
  }, [initializeGraph]);

  // Funciones de control
  const handleFit = () => {
    cyInstance.current?.fit(undefined, 50);
  };



  const handleZoomIn = () => {
    cyInstance.current?.zoom(cyInstance.current.zoom() * 1.2);
    cyInstance.current?.center();
  };

  const handleZoomOut = () => {
    cyInstance.current?.zoom(cyInstance.current.zoom() * 0.8);
    cyInstance.current?.center();
  };

  const handleSearch = useCallback((term: string) => {
    if (!cyInstance.current) return;
    
    cyInstance.current.elements().removeClass('highlighted dimmed');
    
    if (term.trim() === '') return;
    
    const matchingNodes = cyInstance.current.nodes().filter((node) => {
      const label = node.data('label').toLowerCase();
      const nodeData = node.data('nodeData');
      
      return label.includes(term.toLowerCase()) ||
             (nodeData.name && nodeData.name.toLowerCase().includes(term.toLowerCase())) ||
             (nodeData.email && nodeData.email.toLowerCase().includes(term.toLowerCase())) ||
             (nodeData.businessName && nodeData.businessName.toLowerCase().includes(term.toLowerCase()));
    });
    
    if (matchingNodes.length > 0) {
      cyInstance.current.elements().addClass('dimmed');
      matchingNodes.removeClass('dimmed').addClass('highlighted');
      cyInstance.current.fit(matchingNodes, 100);
    }
  }, []);

  const debouncedSearch = useCallback(
    debounce((term: string) => handleSearch(term), 300),
    [handleSearch]
  );

  useEffect(() => {
    debouncedSearch(searchTerm);
  }, [searchTerm, debouncedSearch]);

  const handleClearSearch = () => {
    setSearchTerm('');
    cyInstance.current?.elements().removeClass('highlighted dimmed');
  };

  const handleFilterByType = (type: string) => {
    if (!cyInstance.current) return;
    
    if (activeFilter === type) {
      // Quitar filtro
      setActiveFilter(null);
      cyInstance.current.elements().removeClass('dimmed highlighted');
      cyInstance.current.fit(undefined, 50);
    } else {
      // Aplicar filtro
      setActiveFilter(type);
      const nodesOfType = cyInstance.current.nodes(`[type = "${type}"]`);
      const connectedEdges = nodesOfType.connectedEdges();
      
      cyInstance.current.elements().addClass('dimmed');
      nodesOfType.removeClass('dimmed').addClass('highlighted');
      connectedEdges.removeClass('dimmed').addClass('highlighted');
      
      if (nodesOfType.length > 0) {
        cyInstance.current.fit(nodesOfType, 100);
      }
    }
  };

  const handleToggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleExportPNG = () => {
    if (!cyInstance.current) return;
    
    const png = cyInstance.current.png({
      output: 'blob' as const,
      bg: '#ffffff',
      full: true,
      scale: 2
    }) as Blob;
    
    const link = document.createElement('a');
    link.download = 'graph.png';
    link.href = URL.createObjectURL(png);
    link.click();
  };

  const handleRedistribute = () => {
    if (!cyInstance.current) return;
    
    cyInstance.current.layout({
      name: 'cose-bilkent'
    }).run();
  };

  // Función debounce
  function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait: number
  ): (...args: Parameters<T>) => void {
    let timeout: number;
    return (...args: Parameters<T>) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  }

  const filterButtons = [
    { type: 'person', icon: User, label: 'Personas', color: '#3498db' },
    { type: 'company', icon: Building2, label: 'Empresas', color: '#9b59b6' },
    { type: 'email', icon: Mail, label: 'Emails', color: '#27ae60' },
    { type: 'phone', icon: Phone, label: 'Teléfonos', color: '#e74c3c' },
    { type: 'address', icon: MapPin, label: 'Direcciones', color: '#f39c12' },
    { type: 'domain', icon: Globe, label: 'Dominios', color: '#1abc9c' }
  ];

  return (
    <div className={`graph-container ${isFullscreen ? 'fullscreen' : ''}`} style={{
      position: 'relative',
      width: '100%',
      height: isFullscreen ? '100vh' : '600px',
      backgroundColor: '#000000',
      border: '1px solid #dee2e6',
      borderRadius: '8px',
      overflow: 'hidden',
      display: 'flex'
    }}>
      {/* Toolbar mejorada */}
      <div style={{
        position: 'absolute',
        top: '15px',
        left: '15px',
        right: sidebarOpen ? '320px' : '15px',
        zIndex: 1000,
        display: 'flex',
        gap: '10px',
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        {/* Búsqueda */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          borderRadius: '8px',
          padding: '8px 12px',
          border: '1px solid #dee2e6',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          minWidth: '250px'
        }}>
          <Search className="w-4 h-4" style={{ color: '#6c757d', marginRight: '8px' }} />
          <input
            type="text"
            placeholder="Buscar nodos..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              border: 'none',
              outline: 'none',
              backgroundColor: 'transparent',
              fontSize: '14px',
              flex: 1
            }}
          />
          {searchTerm && (
            <button
              onClick={handleClearSearch}
              style={{
                border: 'none',
                background: 'none',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <X className="w-4 h-4" style={{ color: '#6c757d' }} />
            </button>
          )}
        </div>

        {/* Filtros por tipo */}
        <div style={{
          display: 'flex',
          gap: '5px',
          flexWrap: 'wrap'
        }}>
          {filterButtons.map(({ type, icon: Icon, label, color }) => (
            <button
              key={type}
              onClick={() => handleFilterByType(type)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 12px',
                backgroundColor: activeFilter === type ? color : 'rgba(255, 255, 255, 0.95)',
                color: activeFilter === type ? '#ffffff' : color,
                border: `1px solid ${color}`,
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
              onMouseEnter={(e) => {
                if (activeFilter !== type) {
                  e.currentTarget.style.backgroundColor = color;
                  e.currentTarget.style.color = '#ffffff';
                }
              }}
              onMouseLeave={(e) => {
                if (activeFilter !== type) {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
                  e.currentTarget.style.color = color;
                }
              }}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          ))}
        </div>

        {/* Controles de zoom y acciones */}
        <div style={{
          display: 'flex',
          gap: '5px',
          marginLeft: 'auto'
        }}>
          <button
            onClick={handleZoomIn}
            style={{
              padding: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #dee2e6',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
            title="Acercar"
          >
            <ZoomIn className="w-4 h-4" style={{ color: '#495057' }} />
          </button>
          <button
            onClick={handleZoomOut}
            style={{
              padding: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #dee2e6',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
            title="Alejar"
          >
            <ZoomOut className="w-4 h-4" style={{ color: '#495057' }} />
          </button>
          <button
            onClick={handleFit}
            style={{
              padding: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #dee2e6',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
            title="Ajustar vista"
          >
            <Maximize2 className="w-4 h-4" style={{ color: '#495057' }} />
          </button>
          <button
            onClick={handleRedistribute}
            style={{
              padding: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #dee2e6',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
            title="Redistribuir nodos"
          >
            <Shuffle className="w-4 h-4" style={{ color: '#495057' }} />
          </button>
          <button
            onClick={handleExportPNG}
            style={{
              padding: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #dee2e6',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
            title="Exportar PNG"
          >
            <Download className="w-4 h-4" style={{ color: '#495057' }} />
          </button>
          <button
            onClick={handleToggleFullscreen}
            style={{
              padding: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #dee2e6',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
            title="Pantalla completa"
          >
            <Maximize2 className="w-4 h-4" style={{ color: '#495057' }} />
          </button>
        </div>
      </div>

      {/* Contenedor del grafo */}
      <div 
        ref={cyRef} 
        style={{
          flex: sidebarOpen ? '1' : '1',
          width: sidebarOpen ? 'calc(100% - 300px)' : '100%',
          height: '100%',
          backgroundColor: '#000000',
          transition: 'width 0.3s ease'
        }}
      />

      {/* Panel lateral fijo */}
      {sidebarOpen && selectedNode && (
        <div style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: '300px',
          height: '100%',
          backgroundColor: '#2c3e50',
          color: '#ecf0f1',
          borderLeft: '1px solid #34495e',
          overflowY: 'auto',
          zIndex: 1001,
          transform: sidebarOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s ease'
        }}>
          {/* Header del panel */}
          <div style={{
            padding: '20px',
            borderBottom: '1px solid #34495e',
            backgroundColor: '#34495e'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '10px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {selectedNode.type === 'person' && <User className="w-5 h-5" style={{ color: '#3498db' }} />}
                {selectedNode.type === 'company' && <Building2 className="w-5 h-5" style={{ color: '#9b59b6' }} />}
                {selectedNode.type === 'email' && <Mail className="w-5 h-5" style={{ color: '#27ae60' }} />}
                {selectedNode.type === 'phone' && <Phone className="w-5 h-5" style={{ color: '#e74c3c' }} />}
                {selectedNode.type === 'address' && <MapPin className="w-5 h-5" style={{ color: '#f39c12' }} />}
                {selectedNode.type === 'domain' && <Globe className="w-5 h-5" style={{ color: '#1abc9c' }} />}
                <h5 style={{ margin: 0, color: '#ecf0f1', fontSize: '16px', fontWeight: '600' }}>Detalles</h5>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#bdc3c7',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {/* Título del nodo */}
            <div style={{
              backgroundColor: '#2c3e50',
              padding: '12px',
              borderRadius: '6px',
              border: '1px solid #34495e'
            }}>
              <h6 style={{
                margin: 0,
                color: '#ecf0f1',
                fontSize: '14px',
                fontWeight: '600',
                marginBottom: '4px'
              }}>
                {selectedNode.data.name || selectedNode.data.email || selectedNode.data.number || selectedNode.data.domain || selectedNode.id}
              </h6>
              <small style={{
                color: '#95a5a6',
                fontSize: '12px',
                fontWeight: '500'
              }}>
                {selectedNode.type === 'person' ? 'Persona' :
                 selectedNode.type === 'company' ? 'Empresa' :
                 selectedNode.type === 'email' ? 'Correo Electrónico' :
                 selectedNode.type === 'phone' ? 'Teléfono' :
                 selectedNode.type === 'address' ? 'Dirección' :
                 'Dominio'}
              </small>
            </div>
          </div>

          {/* Contenido del panel - Diseño de cuadrícula */}
          <div style={{ padding: '20px' }}>
            {selectedNode.type === 'person' && (
              <>
                {/* Grid de información personal */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '12px',
                  marginBottom: '20px'
                }}>
                  {/* Tarjeta Nombre */}
                  <div style={{
                    backgroundColor: '#34495e',
                    borderRadius: '8px',
                    padding: '16px',
                    border: '1px solid #4a5f7a',
                    textAlign: 'center'
                  }}>
                    <User className="w-6 h-6" style={{ color: '#000000', marginBottom: '8px', display: 'block', margin: '0 auto 8px auto' }} />
                    <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Nombre</div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px', fontWeight: '600' }}>{selectedNode.data.name}</div>
                  </div>

                  {/* Tarjeta Fecha de Nacimiento */}
                  {selectedNode.data.birthDate && (
                    <div style={{
                      backgroundColor: '#34495e',
                      borderRadius: '8px',
                      padding: '16px',
                      border: '1px solid #4a5f7a',
                      textAlign: 'center'
                    }}>
                      <Calendar className="w-6 h-6" style={{ color: '#000000', marginBottom: '8px', display: 'block', margin: '0 auto 8px auto' }} />
                      <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Nacimiento</div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px', fontWeight: '600' }}>
                        {format(new Date(selectedNode.data.birthDate), 'dd/MM/yyyy', { locale: es })}
                      </div>
                    </div>
                  )}

                  {/* Tarjeta Lugar de Nacimiento */}
                  {selectedNode.data.birthPlace && (
                    <div style={{
                      backgroundColor: '#34495e',
                      borderRadius: '8px',
                      padding: '16px',
                      border: '1px solid #4a5f7a',
                      textAlign: 'center'
                    }}>
                      <MapPin className="w-6 h-6" style={{ color: '#000000', marginBottom: '8px', display: 'block', margin: '0 auto 8px auto' }} />
                      <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Lugar</div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px', fontWeight: '600' }}>{selectedNode.data.birthPlace}</div>
                    </div>
                  )}

                  {/* Tarjeta Género */}
                  {selectedNode.data.gender && (
                    <div style={{
                      backgroundColor: '#34495e',
                      borderRadius: '8px',
                      padding: '16px',
                      border: '1px solid #4a5f7a',
                      textAlign: 'center'
                    }}>
                      <Users className="w-6 h-6" style={{ color: '#000000', marginBottom: '8px', display: 'block', margin: '0 auto 8px auto' }} />
                      <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Género</div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px', fontWeight: '600' }}>{selectedNode.data.gender === 'M' ? 'Masculino' : 'Femenino'}</div>
                    </div>
                  )}
                </div>
                
                {/* Grid de datos calculados */}
                {selectedNode.data.birthDate && (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: '12px',
                    marginBottom: '20px'
                  }}>
                    {/* Tarjeta CURP */}
                    <div style={{
                      backgroundColor: '#34495e',
                      borderRadius: '8px',
                      padding: '16px',
                      border: '1px solid #4a5f7a',
                      textAlign: 'center'
                    }}>
                      <CreditCard className="w-6 h-6" style={{ color: '#000000', marginBottom: '8px', display: 'block', margin: '0 auto 8px auto' }} />
                      <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>CURP</div>
                      <div style={{ color: '#ecf0f1', fontSize: '11px', fontWeight: '600', fontFamily: 'monospace' }}>
                        {calculateCURP(selectedNode.data)}
                      </div>
                    </div>

                    {/* Tarjeta Edad */}
                    <div style={{
                      backgroundColor: '#34495e',
                      borderRadius: '8px',
                      padding: '16px',
                      border: '1px solid #4a5f7a',
                      textAlign: 'center'
                    }}>
                      <Clock className="w-6 h-6" style={{ color: '#000000', marginBottom: '8px', display: 'block', margin: '0 auto 8px auto' }} />
                      <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Edad</div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px', fontWeight: '600' }}>
                        {new Date().getFullYear() - new Date(selectedNode.data.birthDate).getFullYear()} años
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Grid de contacto */}
                {(selectedNode.data.phone || selectedNode.data.email) && (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: '12px',
                    marginBottom: '20px'
                  }}>
                    {/* Tarjeta Teléfono */}
                    {selectedNode.data.phone && (
                      <div style={{
                        backgroundColor: '#34495e',
                        borderRadius: '8px',
                        padding: '16px',
                        border: '1px solid #4a5f7a',
                        textAlign: 'center'
                      }}>
                        <Phone className="w-6 h-6" style={{ color: '#000000', marginBottom: '8px', display: 'block', margin: '0 auto 8px auto' }} />
                        <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Teléfono</div>
                        <div style={{ color: '#ecf0f1', fontSize: '13px', fontWeight: '600' }}>{selectedNode.data.phone}</div>
                      </div>
                    )}

                    {/* Tarjeta Email */}
                    {selectedNode.data.email && (
                      <div style={{
                        backgroundColor: '#34495e',
                        borderRadius: '8px',
                        padding: '16px',
                        border: '1px solid #4a5f7a',
                        textAlign: 'center'
                      }}>
                        <Mail className="w-6 h-6" style={{ color: '#000000', marginBottom: '8px', display: 'block', margin: '0 auto 8px auto' }} />
                        <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Email</div>
                        <div style={{ color: '#ecf0f1', fontSize: '13px', fontWeight: '600' }}>{selectedNode.data.email}</div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
            
            {selectedNode.type === 'company' && (
              <>
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                  gap: '12px', 
                  marginBottom: '16px' 
                }}>
                  {selectedNode.data.businessName && (
                    <div style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <Building2 className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Razón Social</span>
                      </div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.businessName}</div>
                    </div>
                  )}
                  
                  {selectedNode.data.foundedDate && (
                    <div style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <Calendar className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Fecha Constitución</span>
                      </div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px' }}>
                        {format(new Date(selectedNode.data.foundedDate), 'dd/MM/yyyy', { locale: es })}
                      </div>
                    </div>
                  )}
                  
                  {selectedNode.data.industry && (
                    <div style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <Briefcase className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Industria</span>
                      </div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.industry}</div>
                    </div>
                  )}
                  
                  {selectedNode.data.employees && (
                    <div style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <Users className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Empleados</span>
                      </div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.employees}</div>
                    </div>
                  )}
                  
                  {selectedNode.data.foundedDate && (
                    <div style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <Calculator className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>RFC</span>
                      </div>
                      <div style={{
                        backgroundColor: '#ffc107',
                        color: '#000',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontFamily: 'monospace'
                      }}>{calculateRFC(selectedNode.data)}</div>
                    </div>
                  )}
                  
                  {selectedNode.data.foundedDate && (
                    <div style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <Clock className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Años Operación</span>
                      </div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px' }}>
                        {new Date().getFullYear() - new Date(selectedNode.data.foundedDate).getFullYear()} años
                      </div>
                    </div>
                  )}
                  
                  {selectedNode.data.address && (
                    <div style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <MapPin className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Dirección</span>
                      </div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.address}</div>
                    </div>
                  )}
                </div>
              </>
            )}
            
            {selectedNode.type === 'email' && (
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                gap: '12px', 
                marginBottom: '16px' 
              }}>
                {selectedNode.data.email && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Mail className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Dirección Email</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.email}</div>
                  </div>
                )}
                
                {selectedNode.data.domain && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Globe className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Dominio</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.domain}</div>
                  </div>
                )}
                
                {selectedNode.data.provider && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Server className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Proveedor</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.provider}</div>
                  </div>
                )}
                
                {selectedNode.data.verified !== undefined && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Shield className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Verificado</span>
                    </div>
                    <div style={{
                      backgroundColor: selectedNode.data.verified ? '#28a745' : '#dc3545',
                      color: '#fff',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px'
                    }}>
                      {selectedNode.data.verified ? 'Sí' : 'No'}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {selectedNode.type === 'phone' && (
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                gap: '12px', 
                marginBottom: '16px' 
              }}>
                {selectedNode.data.number && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Phone className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Número</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.number}</div>
                  </div>
                )}
                
                {selectedNode.data.carrier && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Wifi className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Operador</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.carrier}</div>
                  </div>
                )}
                
                {selectedNode.data.type && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Smartphone className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Tipo</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.type === 'Mobile' ? 'Móvil' : 'Fijo'}</div>
                  </div>
                )}
                
                {selectedNode.data.location && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <MapPin className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Localización</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.location}</div>
                  </div>
                )}
              </div>
            )}
            
            {selectedNode.type === 'address' && (
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                gap: '12px', 
                marginBottom: '16px' 
              }}>
                {selectedNode.data.street && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <MapPin className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Calle</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.street}</div>
                  </div>
                )}
                
                {selectedNode.data.colony && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Home className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Colonia</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.colony}</div>
                  </div>
                )}
                
                {selectedNode.data.city && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Building className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Ciudad</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.city}</div>
                  </div>
                )}
                
                {selectedNode.data.state && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Flag className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Estado</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.state}</div>
                  </div>
                )}
                
                {selectedNode.data.zipCode && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Hash className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Código Postal</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.zipCode}</div>
                  </div>
                )}
                
                {selectedNode.data.coordinates && (
                  <>
                    <div style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <Navigation className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Latitud</span>
                      </div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.coordinates.lat}</div>
                    </div>
                    
                    <div style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <Navigation className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Longitud</span>
                      </div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.coordinates.lng}</div>
                    </div>
                  </>
                )}
              </div>
            )}
            
            {selectedNode.type === 'domain' && (
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                gap: '12px', 
                marginBottom: '16px' 
              }}>
                {selectedNode.data.domain && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Globe className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Dominio</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.domain}</div>
                  </div>
                )}
                
                {selectedNode.data.registrar && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Building2 className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Registrador</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{selectedNode.data.registrar}</div>
                  </div>
                )}
                
                {selectedNode.data.registrationDate && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Calendar className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Fecha Registro</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>
                      {format(new Date(selectedNode.data.registrationDate), 'dd/MM/yyyy', { locale: es })}
                    </div>
                  </div>
                )}
                
                {selectedNode.data.expirationDate && (
                  <div style={{
                    backgroundColor: '#2c3e50',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #34495e'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                      <Clock className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                      <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>Fecha Expiración</span>
                    </div>
                    <div style={{ color: '#ecf0f1', fontSize: '13px' }}>
                      {format(new Date(selectedNode.data.expirationDate), 'dd/MM/yyyy', { locale: es })}
                    </div>
                  </div>
                )}
                
                {selectedNode.data.nameservers && selectedNode.data.nameservers.length > 0 && (
                  selectedNode.data.nameservers.map((ns: string, nsIndex: number) => (
                    <div key={nsIndex} style={{
                      backgroundColor: '#2c3e50',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid #34495e'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                        <Server className="w-4 h-4" style={{ color: '#000000', marginRight: '8px' }} />
                        <span style={{ color: '#ecf0f1', fontWeight: 'bold', fontSize: '12px' }}>NS{nsIndex + 1}</span>
                      </div>
                      <div style={{ color: '#ecf0f1', fontSize: '13px' }}>{ns}</div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default GraphView;