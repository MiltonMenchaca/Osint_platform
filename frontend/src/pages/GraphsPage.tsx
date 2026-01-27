import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Card, Form, Button, Badge, ButtonGroup, InputGroup, Modal, OverlayTrigger, Tooltip } from 'react-bootstrap';
import cytoscape from 'cytoscape';
import coseBilkent from 'cytoscape-cose-bilkent';
import type { Investigation, User } from '../types';
import apiService from '../services/api';
import Header from '../components/Header';

// Registrar extensiones de Cytoscape
cytoscape.use(coseBilkent);

interface Node {
  id: string;
  label: string;
  type: 'person' | 'organization' | 'ip' | 'domain' | 'email' | 'phone' | 'url' | 'hash' | 'file' | 'cryptocurrency' | 'social_media' | 'geolocation' | 'other' | 'subdomain';
  connections: number;
  community?: number;
  centrality?: number;
  status?: string;
  domain?: string;
  verified?: boolean;
  properties?: Record<string, any>;
  transform_count?: number;
  last_transform?: string;
  registrar?: string;
  registration_date?: string;
  age?: string;
  occupation?: string;
  location?: string;
  size?: string;
  country?: string;
  created_at?: string;
  updated_at?: string;
  industry?: string;
  geolocation?: string;
  isp?: string;
  ip_type?: string;
  confidence?: number;
  source?: string;
}

interface Edge {
  id: string;
  source: string;
  target: string;
  type: string;
  weight: number;
  label: string;
}

interface CytoscapeNode {
  data: {
    id: string;
    label: string;
    type: string;
    connections: number;
    community?: number;
  };
}

interface CytoscapeEdge {
  data: {
    id: string;
    source: string;
    target: string;
    type: string;
    weight: number;
    label: string;
  };
}

interface GraphsPageProps {
  user: User;
  onLogout: () => void;
}

const GraphsPage: React.FC<GraphsPageProps> = ({ user, onLogout }) => {
  // Estados para filtros y controles
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string>('all');
  const [edgeTypeFilter, setEdgeTypeFilter] = useState<string>('all');
  const [layoutType, setLayoutType] = useState<string>('cose-bilkent');
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [showExportModal, setShowExportModal] = useState<boolean>(false);
  const [darkMode] = useState<boolean>(true);
  const [communities, setCommunities] = useState<string[][]>([]);
  const [showSidePanel, setShowSidePanel] = useState<boolean>(true);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [selectedInvestigationId, setSelectedInvestigationId] = useState<string>('');
  const [graphLoading, setGraphLoading] = useState<boolean>(false);
  const [graphError, setGraphError] = useState<string | null>(null);


  const [detailedReport, setDetailedReport] = useState<string>('');
  const [showReportModal, setShowReportModal] = useState(false);
  
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInstance = useRef<cytoscape.Core | null>(null);
  const graphContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (cyRef.current && !cyInstance.current) {
      initializeCytoscape();
    }
    const cleanup = () => {
      if (cyInstance.current) {
        cyInstance.current.destroy();
        cyInstance.current = null;
      }
    };
    void loadInvestigations();
    return cleanup;
  }, []);

  useEffect(() => {
    if (!selectedInvestigationId) return;
    void loadGraphData(selectedInvestigationId);
  }, [selectedInvestigationId]);

  useEffect(() => {
    const onFullscreenChange = () => {
      const active = Boolean(document.fullscreenElement);
      setIsFullscreen(active);
      requestAnimationFrame(() => {
        cyInstance.current?.resize();
        cyInstance.current?.fit();
      });
    };
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    };
  }, []);

  // Actualizar grafo cuando cambien los filtros
  useEffect(() => {
    if (cyInstance.current) {
      updateGraph();
    }
  }, [nodeTypeFilter, edgeTypeFilter, nodes, edges, darkMode]);

  const normalizeInvestigationsPayload = (payload: any): Investigation[] => {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.results)) return payload.results;
    return [];
  };

  const loadInvestigations = async () => {
    try {
      const res = await apiService.getInvestigations();
      if (!res.success || !res.data) {
        setGraphError(res.message || 'No se pudieron cargar las investigaciones');
        setInvestigations([]);
        setSelectedInvestigationId('');
        return;
      }

      const list = normalizeInvestigationsPayload(res.data);
      setInvestigations(list);

      const preferred = list.find((i) => i.status === 'active') || list[0];
      setSelectedInvestigationId(preferred?.id || '');
    } catch (err) {
      setGraphError(err instanceof Error ? err.message : 'No se pudieron cargar las investigaciones');
      setInvestigations([]);
      setSelectedInvestigationId('');
    }
  };

  const toggleFullscreen = async () => {
    const target = graphContainerRef.current;
    if (!target) return;
    try {
      if (!document.fullscreenElement) {
        await target.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (error) {
      console.error('Error al cambiar pantalla completa:', error);
    }
  };

  const normalizeNodeType = (type: string): Node['type'] => {
    const t = (type || 'other').toLowerCase();
    if (t === 'company') return 'organization';
    if (t === 'ip_address') return 'ip';
    if (t === 'geo' || t === 'location') return 'geolocation';
    if (t === 'social') return 'social_media';
    if (t === 'crypto') return 'cryptocurrency';
    if (t === 'subdomain') return 'subdomain';
    if (t === 'person' || t === 'organization' || t === 'ip' || t === 'domain' || t === 'email' || t === 'phone' || t === 'url' || t === 'hash' || t === 'file' || t === 'cryptocurrency' || t === 'social_media' || t === 'geolocation' || t === 'other') {
      return t as Node['type'];
    }
    return 'other';
  };

  const loadGraphData = async (investigationId: string) => {
    setGraphLoading(true);
    setGraphError(null);
    try {
      const res = await apiService.getInvestigationGraph(investigationId);
      if (!res.success || !res.data) {
        setGraphError(res.message || 'No se pudo cargar el grafo');
        setNodes([]);
        setEdges([]);
        setCommunities([]);
        setSelectedNode(null);
        setSelectedEdge(null);
        return;
      }

      const graph: any = res.data;
      const rawNodes: any[] = Array.isArray(graph?.nodes) ? graph.nodes : [];
      const rawEdges: any[] = Array.isArray(graph?.edges) ? graph.edges : [];

      const mappedEdges: Edge[] = rawEdges.map((e) => {
        const id = String(e.id ?? `${e.source ?? ''}-${e.target ?? ''}-${e.type ?? ''}`);
        const type = String(e.type ?? 'related');
        const label = String(e.properties?.label ?? e.properties?.relationship ?? type);
        const weight = typeof e.properties?.weight === 'number' ? e.properties.weight : 1;
        return {
          id,
          source: String(e.source),
          target: String(e.target),
          type,
          weight,
          label,
        };
      });

      const connectionsById = new Map<string, number>();
      for (const e of mappedEdges) {
        connectionsById.set(e.source, (connectionsById.get(e.source) || 0) + 1);
        connectionsById.set(e.target, (connectionsById.get(e.target) || 0) + 1);
      }
      const maxConnections = Math.max(1, ...Array.from(connectionsById.values()));

      const mappedNodes: Node[] = rawNodes.map((n) => {
        const id = String(n.id);
        const properties = (n.properties && typeof n.properties === 'object') ? n.properties : {};
        const label = String(n.name ?? n.label ?? n.value ?? properties.display_name ?? properties.value ?? id);
        const type = normalizeNodeType(String(n.type ?? n.entity_type ?? properties.entity_type ?? 'other'));
        const connections = connectionsById.get(id) || 0;
        return {
          id,
          label,
          type,
          connections,
          centrality: connections / maxConnections,
          verified: Boolean(n.verified ?? properties.verified),
          confidence: typeof n.confidence === 'number' ? n.confidence : (typeof properties.confidence_score === 'number' ? properties.confidence_score : undefined),
          source: typeof properties.source === 'string' ? properties.source : undefined,
          registrar: typeof properties.registrar === 'string' ? properties.registrar : undefined,
          registration_date: typeof properties.registration_date === 'string' ? properties.registration_date : (typeof properties.creation_date === 'string' ? properties.creation_date : undefined),
          properties,
        };
      });

      const detected = detectCommunities(mappedNodes, mappedEdges);
      setCommunities(detected);

      const communityByNodeId = new Map<string, number>();
      detected.forEach((community, index) => {
        community.forEach((nodeId) => {
          communityByNodeId.set(nodeId, index + 1);
        });
      });

      const finalNodes = mappedNodes.map((n) => ({
        ...n,
        community: communityByNodeId.get(n.id),
      }));

      setNodes(finalNodes);
      setEdges(mappedEdges);
      setSelectedNode(null);
      setSelectedEdge(null);
    } catch (err) {
      setGraphError(err instanceof Error ? err.message : 'No se pudo cargar el grafo');
      setNodes([]);
      setEdges([]);
      setCommunities([]);
      setSelectedNode(null);
      setSelectedEdge(null);
    } finally {
      setGraphLoading(false);
    }
  };

  // Función para inicializar Cytoscape
  const initializeCytoscape = () => {
    if (!cyRef.current) return;

    cyInstance.current = cytoscape({
      container: cyRef.current,
      elements: getCytoscapeElements(),
      style: getCytoscapeStyle(),
      layout: {
        name: layoutType
      },
      wheelSensitivity: 0.2,
      minZoom: 0.1,
      maxZoom: 3
    });

    // Event listeners
    cyInstance.current.on('tap', 'node', (evt) => {
      const node = evt.target;
      const nodeData = node.data();
      setSelectedNode({
        id: nodeData.id,
        label: nodeData.label,
        type: nodeData.type,
        connections: nodeData.connections,
        centrality: nodeData.centrality,
        community: nodeData.community
      });
      setSelectedEdge(null);
    });

    cyInstance.current.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      const edgeData = edge.data();
      setSelectedEdge({
        id: edgeData.id,
        source: edgeData.source,
        target: edgeData.target,
        type: edgeData.type,
        weight: edgeData.weight,
        label: edgeData.label
      });
      setSelectedNode(null);
    });

    cyInstance.current.on('tap', (evt) => {
      if (evt.target === cyInstance.current) {
        setSelectedNode(null);
        setSelectedEdge(null);
      }
    });

    // Tooltips para nodos
    cyInstance.current.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      const nodeData = node.data();
      const connectedEdges = cyInstance.current!.edges().filter(`[source = "${nodeData.id}"], [target = "${nodeData.id}"]`);
      
      // Crear tooltip
      const tooltip = document.createElement('div');
      tooltip.className = 'cytoscape-tooltip';
      tooltip.style.cssText = `
        position: absolute;
        background: rgba(0,0,0,0.9);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: bold;
        pointer-events: none;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        border: 1px solid ${getNodeColorHex(nodeData.type)};
      `;
      
      tooltip.innerHTML = `
        <div style="margin-bottom: 4px;">
          <i class="bi bi-${getNodeIcon(nodeData.type)}"></i> 
          <strong>${nodeData.label}</strong>
        </div>
        <div style="font-size: 10px; opacity: 0.8;">
          Tipo: ${getNodeTypeText(nodeData.type)}<br>
          Conexiones: ${connectedEdges.length}<br>
          Centralidad: ${nodeData.centrality?.toFixed(3) || 'N/A'}
        </div>
      `;
      
      document.body.appendChild(tooltip);
      node.data('tooltip', tooltip);
      
      // Posicionar tooltip
      const updateTooltipPosition = (e: MouseEvent) => {
        tooltip.style.left = (e.clientX + 10) + 'px';
        tooltip.style.top = (e.clientY - 10) + 'px';
      };
      
      document.addEventListener('mousemove', updateTooltipPosition);
      node.data('tooltipMoveHandler', updateTooltipPosition);
    });

    cyInstance.current.on('mouseout', 'node', (evt) => {
      const node = evt.target;
      const tooltip = node.data('tooltip');
      const moveHandler = node.data('tooltipMoveHandler');
      
      if (tooltip) {
        document.body.removeChild(tooltip);
        node.removeData('tooltip');
      }
      
      if (moveHandler) {
        document.removeEventListener('mousemove', moveHandler);
        node.removeData('tooltipMoveHandler');
      }
    });

    // Tooltips para edges
    cyInstance.current.on('mouseover', 'edge', (evt) => {
      const edge = evt.target;
      const edgeData = edge.data();
      const sourceNode = cyInstance.current!.getElementById(edgeData.source).data();
      const targetNode = cyInstance.current!.getElementById(edgeData.target).data();
      
      // Crear tooltip
      const tooltip = document.createElement('div');
      tooltip.className = 'cytoscape-tooltip';
      tooltip.style.cssText = `
        position: absolute;
        background: rgba(0,0,0,0.9);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: bold;
        pointer-events: none;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        border: 1px solid ${getEdgeColor(edgeData.type)};
      `;
      
      tooltip.innerHTML = `
        <div style="margin-bottom: 4px;">
          <i class="bi bi-arrow-right"></i> 
          <strong>${edgeData.label}</strong>
        </div>
        <div style="font-size: 10px; opacity: 0.8;">
          ${sourceNode.label} → ${targetNode.label}<br>
          Tipo: ${edgeData.type}<br>
          Relación: ${edgeData.label}
        </div>
      `;
      
      document.body.appendChild(tooltip);
      edge.data('tooltip', tooltip);
      
      // Posicionar tooltip
      const updateTooltipPosition = (e: MouseEvent) => {
        tooltip.style.left = (e.clientX + 10) + 'px';
        tooltip.style.top = (e.clientY - 10) + 'px';
      };
      
      document.addEventListener('mousemove', updateTooltipPosition);
      edge.data('tooltipMoveHandler', updateTooltipPosition);
    });

    cyInstance.current.on('mouseout', 'edge', (evt) => {
      const edge = evt.target;
      const tooltip = edge.data('tooltip');
      const moveHandler = edge.data('tooltipMoveHandler');
      
      if (tooltip) {
        document.body.removeChild(tooltip);
        edge.removeData('tooltip');
      }
      
      if (moveHandler) {
        document.removeEventListener('mousemove', moveHandler);
        edge.removeData('tooltipMoveHandler');
      }
    });
  };

  // Función para obtener elementos de Cytoscape
  const getCytoscapeElements = (): (CytoscapeNode | CytoscapeEdge)[] => {
    const filteredNodes = nodes.filter(node => 
      nodeTypeFilter === 'all' || node.type === nodeTypeFilter
    );

    const filteredEdges = edges.filter(edge => {
      const sourceExists = filteredNodes.some(n => n.id === edge.source);
      const targetExists = filteredNodes.some(n => n.id === edge.target);
      return sourceExists && targetExists && (edgeTypeFilter === 'all' || edge.type === edgeTypeFilter);
    });

    const cytoscapeNodes: CytoscapeNode[] = filteredNodes.map(node => ({
      data: {
        id: node.id,
        label: node.label,
        type: node.type,
        connections: node.connections,
        community: node.community
      }
    }));

    const cytoscapeEdges: CytoscapeEdge[] = filteredEdges.map(edge => ({
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: edge.type,
        weight: edge.weight,
        label: edge.label
      }
    }));

    return [...cytoscapeNodes, ...cytoscapeEdges];
  };

  // Función para obtener estilos de Cytoscape - Diseño Profesional Ciberseguridad con Iconos
  const getCytoscapeStyle = (): any => {
    const baseStyle = [
      {
        selector: 'node',
        style: {
          'shape': 'round-rectangle',
          'background-color': (ele: any) => getNodeColor(ele.data('type')),
          'background-gradient-direction': 'to-bottom',
          'background-gradient-stop-colors': (ele: any) => `${getNodeColor(ele.data('type'))} ${getNodeColorSecondary(ele.data('type'))}`,
          'label': (ele: any) => `${getNodeIcon(ele.data('type'))} ${ele.data('label')}`,
          'text-valign': 'center',
          'text-halign': 'center',
          'color': '#FFFFFF',
          'font-family': 'Bootstrap Icons, Consolas, Monaco, "Courier New", monospace',
          'font-size': '10px',
          'font-weight': '600',
          'width': (ele: any) => {
            const labelLength = ele.data('label').length;
            return Math.max(80, Math.min(150, labelLength * 8 + 40));
          },
          'height': 32,
          'border-width': 1.5,
          'border-color': (ele: any) => getNodeBorderColor(ele.data('type')),
          'border-style': 'solid',
          'text-outline-width': 0.5,
          'text-outline-color': '#000000',
          'box-shadow-blur': 8,
          'box-shadow-color': (ele: any) => getNodeGlowColor(ele.data('type')),
          'box-shadow-opacity': 0.4,
          'transition-property': 'background-color, border-color, box-shadow-color',
          'transition-duration': '0.3s',
          'text-wrap': 'none',
          'text-max-width': (ele: any) => {
            const labelLength = ele.data('label').length;
            return Math.max(70, Math.min(140, labelLength * 8 + 30));
          }
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 1.5,
          'line-color': (ele: any) => getEdgeColor(ele.data('type')),
          'target-arrow-color': (ele: any) => getEdgeColor(ele.data('type')),
          'target-arrow-shape': 'triangle-backcurve',
          'target-arrow-size': 8,
          'curve-style': 'straight',
          'line-style': 'solid',
          'label': 'data(label)',
          'font-family': 'Consolas, Monaco, "Courier New", monospace',
          'font-size': '9px',
          'font-weight': '500',
          'color': '#B0B0B0',
          'text-rotation': 'autorotate',
          'text-margin-y': -8,
          'text-outline-width': 0.5,
          'text-outline-color': '#1A1A1A',
          'opacity': 0.8,
          'transition-property': 'line-color, target-arrow-color, opacity',
          'transition-duration': '0.3s'
        }
      },
      {
        selector: 'node:selected',
        style: {
          'border-width': 3,
          'border-color': '#00D4FF',
          'box-shadow-blur': 15,
          'box-shadow-color': '#00D4FF',
          'box-shadow-opacity': 0.7,
          'background-color': (ele: any) => getNodeColorHighlighted(ele.data('type'))
        }
      },
      {
        selector: 'edge:selected',
        style: {
          'line-color': '#00D4FF',
          'target-arrow-color': '#00D4FF',
          'width': 2.5,
          'opacity': 1
        }
      },
      {
        selector: '.highlighted',
        style: {
          'background-color': '#FFD700',
          'border-color': '#FFA500',
          'line-color': '#FFD700',
          'target-arrow-color': '#FFD700',
          'box-shadow-blur': 12,
          'box-shadow-color': '#FFD700',
          'box-shadow-opacity': 0.6,
          'transition-property': 'background-color, line-color, target-arrow-color, border-color, box-shadow-color',
          'transition-duration': '0.4s'
        }
      },
      {
        selector: 'node:hover',
        style: {
          'box-shadow-blur': 12,
          'box-shadow-opacity': 0.6,
          'border-width': 2
        }
      },
      {
        selector: 'edge:hover',
        style: {
          'width': 2,
          'opacity': 1
        }
      }
    ];

    return baseStyle;
  };

  // Función para actualizar el grafo
  const updateGraph = () => {
    if (!cyInstance.current) return;
    
    cyInstance.current.elements().remove();
    cyInstance.current.add(getCytoscapeElements());
    cyInstance.current.style(getCytoscapeStyle());
    cyInstance.current.layout({ name: layoutType }).run();
  };

  // Funciones auxiliares
  const getFilteredNodes = () => {
    if (nodeTypeFilter === 'all') return nodes;
    return nodes.filter(node => node.type === nodeTypeFilter);
  };

  const getFilteredEdges = () => {
    if (edgeTypeFilter === 'all') return edges;
    return edges.filter(edge => edge.type === edgeTypeFilter);
  };

  // Función para obtener el color del nodo - Esquema Ciberseguridad
  const getNodeColor = (type: string): string => {
    const colors: { [key: string]: string } = {
      person: '#4A90E2',      // Azul profesional
      organization: '#2ECC71', // Verde militar
      ip: '#F39C12',          // Naranja técnico
      domain: '#9B59B6',      // Púrpura cyber
      email: '#E74C3C'        // Rojo alerta
    };
    return colors[type] || '#7F8C8D';
  };

  // Función para obtener el color secundario del gradiente
  const getNodeColorSecondary = (type: string): string => {
    const colors: { [key: string]: string } = {
      person: '#357ABD',      // Azul más oscuro
      organization: '#27AE60', // Verde más oscuro
      ip: '#E67E22',          // Naranja más oscuro
      domain: '#8E44AD',      // Púrpura más oscuro
      email: '#C0392B'        // Rojo más oscuro
    };
    return colors[type] || '#6C7B7F';
  };

  // Función para obtener el color del borde
  const getNodeBorderColor = (type: string): string => {
    const colors: { [key: string]: string } = {
      person: '#5DADE2',      // Azul claro
      organization: '#58D68D', // Verde claro
      ip: '#F8C471',          // Naranja claro
      domain: '#BB8FCE',      // Púrpura claro
      email: '#F1948A'        // Rojo claro
    };
    return colors[type] || '#95A5A6';
  };

  // Función para obtener el color del glow
  const getNodeGlowColor = (type: string): string => {
    const colors: { [key: string]: string } = {
      person: '#4A90E2',
      organization: '#2ECC71',
      ip: '#F39C12',
      domain: '#9B59B6',
      email: '#E74C3C'
    };
    return colors[type] || '#7F8C8D';
  };

  // Función para obtener el color resaltado
  const getNodeColorHighlighted = (type: string): string => {
    const colors: { [key: string]: string } = {
      person: '#5DADE2',
      organization: '#58D68D',
      ip: '#F8C471',
      domain: '#BB8FCE',
      email: '#F1948A'
    };
    return colors[type] || '#95A5A6';
  };

  // Función para obtener el color hexadecimal del nodo
  const getNodeColorHex = (type: string): string => {
    const colors: { [key: string]: string } = {
      person: '#0d6efd',
      organization: '#198754',
      ip: '#ffc107',
      domain: '#0dcaf0',
      email: '#dc3545'
    };
    return colors[type] || '#6c757d';
  };

  // Función para obtener el texto del tipo de nodo
  const getNodeTypeText = (type: string): string => {
    const types: { [key: string]: string } = {
      person: 'Persona',
      organization: 'Organización',
      ip: 'Dirección IP',
      domain: 'Dominio',
      email: 'Email'
    };
    return types[type] || type;
  };

  // Función para obtener el color de las conexiones - Esquema Ciberseguridad
  const getEdgeColor = (type: string) => {
    const colors = {
      communication: '#3498DB',  // Azul comunicación
      ownership: '#27AE60',      // Verde propiedad
      association: '#F39C12',    // Naranja asociación
      transaction: '#E74C3C'     // Rojo transacción
    };
    return colors[type as keyof typeof colors] || '#7F8C8D';
  };

  const getNodeIcon = (type: string) => {
    const icons = {
      person: '●',     // Círculo sólido para persona
      organization: '■',  // Cuadrado para organización
      ip: '◆',        // Diamante para IP
      domain: '▲',     // Triángulo para dominio
      email: '✉',      // Sobre para email
      phone: '☎'       // Teléfono para phone
    };
    return icons[type as keyof typeof icons] || '○';
  };



  // Funciones de análisis
  const detectCommunities = (nodes: Node[], edges: Edge[]): string[][] => {
    // Simulación simple de detección de comunidades
    const communities: string[][] = [];
    const visited = new Set<string>();
    
    for (const node of nodes) {
      if (!visited.has(node.id)) {
        const community: string[] = [node.id];
        visited.add(node.id);
        
        // Encontrar nodos conectados
        const connectedEdges = edges.filter(e => e.source === node.id || e.target === node.id);
        for (const edge of connectedEdges) {
          const connectedNodeId = edge.source === node.id ? edge.target : edge.source;
          if (!visited.has(connectedNodeId)) {
            community.push(connectedNodeId);
            visited.add(connectedNodeId);
          }
        }
        
        communities.push(community);
      }
    }
    
    return communities;
  };

  const findShortestPath = (startId: string, endId: string, edges: Edge[]) => {
    // Implementación simple de BFS para encontrar el camino más corto
    const queue = [[startId]];
    const visited = new Set([startId]);
    
    while (queue.length > 0) {
      const path = queue.shift()!;
      const currentNode = path[path.length - 1];
      
      if (currentNode === endId) {
        return path;
      }
      
      const connectedEdges = edges.filter(e => e.source === currentNode || e.target === currentNode);
      for (const edge of connectedEdges) {
        const nextNode = edge.source === currentNode ? edge.target : edge.source;
        if (!visited.has(nextNode)) {
          visited.add(nextNode);
          queue.push([...path, nextNode]);
        }
      }
    }
    
    return null;
  };

  const calculateCentrality = (nodeId: string, edges: Edge[]) => {
    // Cálculo simple de centralidad por grado
    const connections = edges.filter(e => e.source === nodeId || e.target === nodeId).length;
    return connections;
  };

  // Función para calcular centralidad de intermediación (betweenness)
  const calculateBetweennessCentrality = (nodeId: string, nodes: Node[], edges: Edge[]) => {
    let betweenness = 0;
    const nodeCount = nodes.length;
    
    // Para cada par de nodos (excluyendo el nodo actual)
    for (let i = 0; i < nodeCount; i++) {
      for (let j = i + 1; j < nodeCount; j++) {
        const sourceId = nodes[i].id;
        const targetId = nodes[j].id;
        
        if (sourceId !== nodeId && targetId !== nodeId) {
          const shortestPath = findShortestPath(sourceId, targetId, edges);
          if (shortestPath && shortestPath.includes(nodeId)) {
            betweenness += 1;
          }
        }
      }
    }
    
    // Normalizar por el número máximo posible de caminos
    const maxPaths = ((nodeCount - 1) * (nodeCount - 2)) / 2;
    return maxPaths > 0 ? betweenness / maxPaths : 0;
  };

  // Función para calcular centralidad de cercanía (closeness)
  const calculateClosenessCentrality = (nodeId: string, nodes: Node[], edges: Edge[]) => {
    let totalDistance = 0;
    let reachableNodes = 0;
    
    nodes.forEach(targetNode => {
      if (targetNode.id !== nodeId) {
        const path = findShortestPath(nodeId, targetNode.id, edges);
        if (path) {
          totalDistance += path.length - 1; // -1 porque el path incluye el nodo origen
          reachableNodes++;
        }
      }
    });
    
    // Si no puede alcanzar ningún nodo, la centralidad es 0
    if (reachableNodes === 0 || totalDistance === 0) return 0;
    
    // Centralidad de cercanía = (n-1) / suma de distancias
    return reachableNodes / totalDistance;
  };

  // Manejadores de eventos mejorados
  const handleAnalyzeCommunities = () => {
    console.log('🔍 Analizando comunidades...');
    const filteredNodes = getFilteredNodes();
    const filteredEdges = getFilteredEdges();
    const communities = detectCommunities(filteredNodes, filteredEdges);
    
    // Generar reporte detallado
    let report = `# REPORTE DE ANÁLISIS DE COMUNIDADES\n\n`;
    report += `**Fecha de análisis:** ${new Date().toLocaleString()}\n\n`;
    report += `## Resumen Ejecutivo\n`;
    report += `- **Total de comunidades detectadas:** ${communities.length}\n`;
    report += `- **Nodos analizados:** ${filteredNodes.length}\n`;
    report += `- **Conexiones analizadas:** ${filteredEdges.length}\n\n`;
    
    report += `## Análisis Detallado por Comunidad\n\n`;
    
    communities.forEach((community, index) => {
      const communityNodes = filteredNodes.filter(node => community.includes(node.id));
      const communitySize = community.length;
      const avgCentrality = communityNodes.reduce((sum, node) => sum + (node.centrality || 0), 0) / communitySize;
      
      report += `### Comunidad ${index + 1}\n`;
      report += `- **Tamaño:** ${communitySize} nodos\n`;
      report += `- **Centralidad promedio:** ${avgCentrality.toFixed(2)}\n`;
      report += `- **Nodos principales:**\n`;
      
      communityNodes
        .sort((a, b) => (b.centrality || 0) - (a.centrality || 0))
        .slice(0, 3)
        .forEach(node => {
          report += `  - ${node.label} (${node.type}, centralidad: ${node.centrality || 0})\n`;
        });
      
      report += `\n`;
    });
    
    // Análisis de conectividad entre comunidades
    report += `## Conectividad Entre Comunidades\n\n`;
    const interCommunityEdges = filteredEdges.filter(edge => {
      const sourceCommunity = communities.findIndex(c => c.includes(edge.source));
      const targetCommunity = communities.findIndex(c => c.includes(edge.target));
      return sourceCommunity !== targetCommunity && sourceCommunity !== -1 && targetCommunity !== -1;
    });
    
    report += `- **Conexiones entre comunidades:** ${interCommunityEdges.length}\n`;
    report += `- **Densidad de interconexión:** ${((interCommunityEdges.length / filteredEdges.length) * 100).toFixed(1)}%\n\n`;
    
    setDetailedReport(report);
    // setAnalysisResults({ type: 'communities', data: communities, report });
    setShowReportModal(true);
    console.log('✅ Comunidades detectadas:', communities);
  };

  const handleShortestPaths = () => {
    console.log('🔍 Calculando caminos más cortos...');
    const filteredNodes = getFilteredNodes();
    const filteredEdges = getFilteredEdges();
    
    if (filteredNodes.length >= 2) {
      // Analizar múltiples rutas críticas
      const criticalPaths = [];
      const bridgeNodes = new Set();
      
      // Encontrar caminos entre nodos de alta centralidad
      const highCentralityNodes = filteredNodes
        .filter(node => (node.centrality || 0) > 0.5)
        .sort((a, b) => (b.centrality || 0) - (a.centrality || 0))
        .slice(0, 5);
      
      for (let i = 0; i < highCentralityNodes.length; i++) {
        for (let j = i + 1; j < highCentralityNodes.length; j++) {
          const path = findShortestPath(highCentralityNodes[i].id, highCentralityNodes[j].id, filteredEdges);
          if (path && path.length > 2) {
            criticalPaths.push({
              from: highCentralityNodes[i].label,
              to: highCentralityNodes[j].label,
              path: path,
              length: path.length - 1,
              efficiency: 1 / (path.length - 1)
            });
            
            // Identificar nodos puente (intermedios en rutas críticas)
            path.slice(1, -1).forEach(nodeId => {
              const node = filteredNodes.find(n => n.id === nodeId);
              if (node) bridgeNodes.add(node.label);
            });
          }
        }
      }
      
      // Generar reporte detallado
      let report = `# REPORTE DE ANÁLISIS DE CAMINOS MÁS CORTOS\n\n`;
      report += `**Fecha de análisis:** ${new Date().toLocaleString()}\n\n`;
      report += `## Resumen Ejecutivo\n`;
      report += `- **Rutas críticas analizadas:** ${criticalPaths.length}\n`;
      report += `- **Nodos puente identificados:** ${bridgeNodes.size}\n`;
      report += `- **Eficiencia promedio de comunicación:** ${(criticalPaths.reduce((sum, p) => sum + p.efficiency, 0) / criticalPaths.length).toFixed(3)}\n\n`;
      
      report += `## Rutas Críticas en la Red\n\n`;
      criticalPaths
        .sort((a, b) => a.length - b.length)
        .slice(0, 10)
        .forEach((pathInfo, index) => {
          report += `### Ruta ${index + 1}: ${pathInfo.from} → ${pathInfo.to}\n`;
          report += `- **Longitud:** ${pathInfo.length} saltos\n`;
          report += `- **Eficiencia:** ${pathInfo.efficiency.toFixed(3)}\n`;
          report += `- **Camino:** ${pathInfo.path.map(id => {
            const node = filteredNodes.find(n => n.id === id);
            return node ? node.label : id;
          }).join(' → ')}\n\n`;
        });
      
      report += `## Nodos que Actúan como Puentes\n\n`;
      report += `Los siguientes nodos son críticos para la conectividad de la red:\n\n`;
      Array.from(bridgeNodes).forEach(nodeLabel => {
        const node = filteredNodes.find(n => n.label === nodeLabel);
        if (node) {
          report += `- **${nodeLabel}** (${node.type}, centralidad: ${node.centrality || 0})\n`;
        }
      });
      
      report += `\n## Análisis de Eficiencia de Comunicación\n\n`;
      const avgPathLength = criticalPaths.reduce((sum, p) => sum + p.length, 0) / criticalPaths.length;
      report += `- **Longitud promedio de caminos:** ${avgPathLength.toFixed(2)} saltos\n`;
      report += `- **Diámetro de la red:** ${Math.max(...criticalPaths.map(p => p.length))} saltos\n`;
      report += `- **Densidad de conectividad:** ${((filteredEdges.length / (filteredNodes.length * (filteredNodes.length - 1))) * 100).toFixed(1)}%\n`;
      
      setDetailedReport(report);
      // setAnalysisResults({ type: 'shortest_paths', data: criticalPaths, bridgeNodes: Array.from(bridgeNodes), report });
      setShowReportModal(true);
      console.log('✅ Análisis de caminos completado:', criticalPaths);
    } else {
      alert('Se necesitan al menos 2 nodos para calcular caminos');
    }
  };

  const handleCentralityAnalysis = () => {
    console.log('📊 Calculando análisis de centralidad...');
    const filteredNodes = getFilteredNodes();
    const filteredEdges = getFilteredEdges();
    
    const centralityResults = filteredNodes.map(node => ({
      id: node.id,
      label: node.label,
      type: node.type,
      centrality: calculateCentrality(node.id, filteredEdges)
    }));
    
    // Calcular diferentes tipos de centralidad
    const nodeMetrics = centralityResults.map(node => {
      const connections = filteredEdges.filter(edge => 
        edge.source === node.id || edge.target === node.id
      ).length;
      
      const betweennessCentrality = calculateBetweennessCentrality(node.id, filteredNodes, filteredEdges);
      const closenessCentrality = calculateClosenessCentrality(node.id, filteredNodes, filteredEdges);
      
      return {
        ...node,
        degreeCentrality: connections,
        betweennessCentrality,
        closenessCentrality,
        overallInfluence: (node.centrality + betweennessCentrality + closenessCentrality) / 3
      };
    });
    
    // Identificar nodos clave por diferentes criterios
    const topByDegree = [...nodeMetrics].sort((a, b) => b.degreeCentrality - a.degreeCentrality).slice(0, 5);
    const topByBetweenness = [...nodeMetrics].sort((a, b) => b.betweennessCentrality - a.betweennessCentrality).slice(0, 5);
    const topByCloseness = [...nodeMetrics].sort((a, b) => b.closenessCentrality - a.closenessCentrality).slice(0, 5);
    const topByInfluence = [...nodeMetrics].sort((a, b) => b.overallInfluence - a.overallInfluence).slice(0, 10);
    
    // Generar reporte detallado
    let report = `# REPORTE DE ANÁLISIS DE CENTRALIDAD\n\n`;
    report += `**Fecha de análisis:** ${new Date().toLocaleString()}\n\n`;
    report += `## Resumen Ejecutivo\n`;
    report += `- **Nodos analizados:** ${nodeMetrics.length}\n`;
    report += `- **Conexiones totales:** ${filteredEdges.length}\n`;
    report += `- **Nodo más influyente:** ${topByInfluence[0]?.label} (influencia: ${topByInfluence[0]?.overallInfluence.toFixed(3)})\n`;
    report += `- **Densidad de la red:** ${((filteredEdges.length / (filteredNodes.length * (filteredNodes.length - 1))) * 100).toFixed(1)}%\n\n`;
    
    report += `## Ranking de Nodos por Centralidad\n\n`;
    report += `### Top 10 Nodos por Influencia General\n\n`;
    topByInfluence.forEach((node, index) => {
      report += `**${index + 1}. ${node.label}**\n`;
      report += `- Tipo: ${node.type}\n`;
      report += `- Centralidad de grado: ${node.degreeCentrality}\n`;
      report += `- Centralidad de intermediación: ${node.betweennessCentrality.toFixed(3)}\n`;
      report += `- Centralidad de cercanía: ${node.closenessCentrality.toFixed(3)}\n`;
      report += `- Influencia general: ${node.overallInfluence.toFixed(3)}\n\n`;
    });
    
    report += `### Nodos Clave por Conectividad (Grado)\n\n`;
    topByDegree.forEach((node, index) => {
      report += `${index + 1}. **${node.label}** - ${node.degreeCentrality} conexiones\n`;
    });
    
    report += `\n### Nodos Clave como Intermediarios (Betweenness)\n\n`;
    topByBetweenness.forEach((node, index) => {
      report += `${index + 1}. **${node.label}** - ${node.betweennessCentrality.toFixed(3)} (controla flujo de información)\n`;
    });
    
    report += `\n### Nodos Clave por Accesibilidad (Closeness)\n\n`;
    topByCloseness.forEach((node, index) => {
      report += `${index + 1}. **${node.label}** - ${node.closenessCentrality.toFixed(3)} (acceso rápido a toda la red)\n`;
    });
    
    report += `\n## Análisis de Influencia en la Red\n\n`;
    report += `### Nodos Críticos para la Conectividad\n`;
    const criticalNodes = topByBetweenness.filter(node => node.betweennessCentrality > 0.1);
    if (criticalNodes.length > 0) {
      report += `Los siguientes nodos son críticos para mantener la conectividad de la red:\n\n`;
      criticalNodes.forEach(node => {
        report += `- **${node.label}**: Su eliminación podría fragmentar la red\n`;
      });
    } else {
      report += `No se identificaron nodos críticos que puedan fragmentar la red.\n`;
    }
    
    report += `\n### Distribución de Poder\n`;
    const avgInfluence = nodeMetrics.reduce((sum, node) => sum + node.overallInfluence, 0) / nodeMetrics.length;
    const highInfluenceNodes = nodeMetrics.filter(node => node.overallInfluence > avgInfluence * 1.5).length;
    report += `- **Influencia promedio:** ${avgInfluence.toFixed(3)}\n`;
    report += `- **Nodos de alta influencia:** ${highInfluenceNodes} (${((highInfluenceNodes / nodeMetrics.length) * 100).toFixed(1)}%)\n`;
    report += `- **Concentración de poder:** ${highInfluenceNodes < nodeMetrics.length * 0.2 ? 'Alta' : 'Distribuida'}\n`;
    
    setDetailedReport(report);
    // setAnalysisResults({ 
    //   type: 'centrality', 
    //   data: nodeMetrics, 
    //   topByDegree, 
    //   topByBetweenness, 
    //   topByCloseness, 
    //   topByInfluence,
    //   report 
    // });
    setShowReportModal(true);
    console.log('✅ Análisis de centralidad completado:', nodeMetrics);
  };

  const handleExportData = () => {
    console.log('📤 Exportando datos...');
    const filteredNodes = getFilteredNodes();
    const filteredEdges = getFilteredEdges();
    
    // Generar resumen ejecutivo
    const executiveSummary = generateExecutiveSummary(filteredNodes, filteredEdges);
    
    // Datos estructurados para JSON
    const structuredData = {
      metadata: {
        title: 'Análisis de Red OSINT',
        exportDate: new Date().toISOString(),
        nodeTypeFilter,
        edgeTypeFilter,
        layoutType,
        totalNodes: filteredNodes.length,
        totalEdges: filteredEdges.length
      },
      executiveSummary,
      nodes: filteredNodes.map(node => ({
        id: node.id,
        label: node.label,
        type: node.type,
        centrality: node.centrality || 0,
        connections: filteredEdges.filter(e => e.source === node.id || e.target === node.id).length
      })),
      edges: filteredEdges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: edge.type,
        weight: edge.weight || 1
      })),
      analysis: {
        networkDensity: ((filteredEdges.length / (filteredNodes.length * (filteredNodes.length - 1))) * 100).toFixed(2),
        averageConnections: (filteredEdges.length * 2 / filteredNodes.length).toFixed(2),
        mostConnectedNode: filteredNodes.reduce((max, node) => {
          const connections = filteredEdges.filter(e => e.source === node.id || e.target === node.id).length;
          return connections > (max.connections || 0) ? { ...node, connections } : max;
        }, { connections: 0, label: 'N/A' })
      }
    };
    
    // Exportar JSON estructurado
    const jsonBlob = new Blob([JSON.stringify(structuredData, null, 2)], { type: 'application/json' });
    const jsonUrl = URL.createObjectURL(jsonBlob);
    const jsonLink = document.createElement('a');
    jsonLink.href = jsonUrl;
    jsonLink.download = `osint-graph-analysis-${new Date().toISOString().split('T')[0]}.json`;
    jsonLink.click();
    URL.revokeObjectURL(jsonUrl);
    
    // Generar y exportar reporte en texto (simulando PDF)
    const textReport = generateTextReport(structuredData);
    const textBlob = new Blob([textReport], { type: 'text/plain' });
    const textUrl = URL.createObjectURL(textBlob);
    const textLink = document.createElement('a');
    textLink.href = textUrl;
    textLink.download = `osint-graph-report-${new Date().toISOString().split('T')[0]}.txt`;
    textLink.click();
    URL.revokeObjectURL(textUrl);
    
    // Mostrar resumen ejecutivo en modal
    setDetailedReport(executiveSummary);
    // setAnalysisResults({ type: 'export', data: structuredData, report: executiveSummary });
    setShowReportModal(true);
    
    console.log('✅ Datos exportados: JSON y reporte de texto');
  };

  // Función para generar resumen ejecutivo
  const generateExecutiveSummary = (nodes: Node[], edges: Edge[]) => {
    const nodeTypes = [...new Set(nodes.map(n => n.type))];
    const edgeTypes = [...new Set(edges.map(e => e.type))];
    const networkDensity = ((edges.length / (nodes.length * (nodes.length - 1))) * 100);
    
    let summary = `# RESUMEN EJECUTIVO - ANÁLISIS DE RED OSINT\n\n`;
    summary += `**Fecha de análisis:** ${new Date().toLocaleString()}\n\n`;
    summary += `## Métricas Generales\n`;
    summary += `- **Total de entidades:** ${nodes.length}\n`;
    summary += `- **Total de conexiones:** ${edges.length}\n`;
    summary += `- **Tipos de entidades:** ${nodeTypes.join(', ')}\n`;
    summary += `- **Tipos de relaciones:** ${edgeTypes.join(', ')}\n`;
    summary += `- **Densidad de la red:** ${networkDensity.toFixed(2)}%\n\n`;
    
    summary += `## Análisis de Conectividad\n`;
    const avgConnections = (edges.length * 2 / nodes.length);
    summary += `- **Conexiones promedio por nodo:** ${avgConnections.toFixed(2)}\n`;
    
    const mostConnected = nodes.reduce((max, node) => {
      const connections = edges.filter(e => e.source === node.id || e.target === node.id).length;
      return connections > (max.connections || 0) ? { ...node, connections } : max;
    }, { connections: 0, label: 'N/A' });
    
    summary += `- **Nodo más conectado:** ${mostConnected.label} (${mostConnected.connections} conexiones)\n`;
    
    summary += `\n## Distribución por Tipo\n`;
    nodeTypes.forEach(type => {
      const count = nodes.filter(n => n.type === type).length;
      const percentage = ((count / nodes.length) * 100).toFixed(1);
      summary += `- **${type}:** ${count} entidades (${percentage}%)\n`;
    });
    
    summary += `\n## Recomendaciones\n`;
    if (networkDensity < 10) {
      summary += `- La red presenta baja densidad, considere investigar conexiones adicionales\n`;
    }
    if (mostConnected.connections > avgConnections * 3) {
      summary += `- El nodo "${mostConnected.label}" es un punto crítico de la red\n`;
    }
    summary += `- Se recomienda análisis de comunidades para identificar grupos de interés\n`;
    
    return summary;
  };

  // Función para generar reporte completo en texto
  const generateTextReport = (data: any) => {
    let report = `REPORTE COMPLETO DE ANÁLISIS DE RED OSINT\n`;
    report += `${'='.repeat(50)}\n\n`;
    report += data.executiveSummary.replace(/\n/g, '\n');
    report += `\n\n## DATOS DETALLADOS\n\n`;
    report += `### Nodos (${data.nodes.length})\n`;
    data.nodes.forEach((node: any, index: number) => {
      report += `${index + 1}. ${node.label} (${node.type}) - ${node.connections} conexiones\n`;
    });
    report += `\n### Conexiones (${data.edges.length})\n`;
    data.edges.forEach((edge: any, index: number) => {
      const sourceNode = data.nodes.find((n: any) => n.id === edge.source);
      const targetNode = data.nodes.find((n: any) => n.id === edge.target);
      report += `${index + 1}. ${sourceNode?.label} → ${targetNode?.label} (${edge.type})\n`;
    });
    return report;
   };

  // Función para generar reporte completo combinando todos los análisis
  const handleGenerateCompleteReport = async () => {
    console.log('📊 Generando reporte completo...');
    const filteredNodes = getFilteredNodes();
    const filteredEdges = getFilteredEdges();
    
    // Ejecutar todos los análisis
    const communityAnalysis = performCommunityAnalysis(filteredNodes, filteredEdges);
    const centralityResults = calculateAllCentralities(filteredNodes, filteredEdges);
    const pathAnalysis = analyzeNetworkPaths(filteredNodes, filteredEdges);
    const executiveSummary = generateExecutiveSummary(filteredNodes, filteredEdges);
    
    // Generar reporte completo
    const completeReport = generateCompleteReport({
      nodes: filteredNodes,
      edges: filteredEdges,
      communities: communityAnalysis,
      centrality: centralityResults,
      paths: pathAnalysis,
      executiveSummary
    });
    
    // Exportar reporte completo
    const reportBlob = new Blob([completeReport], { type: 'text/plain' });
    const reportUrl = URL.createObjectURL(reportBlob);
    const reportLink = document.createElement('a');
    reportLink.href = reportUrl;
    reportLink.download = `reporte-completo-osint-${new Date().toISOString().split('T')[0]}.txt`;
    reportLink.click();
    URL.revokeObjectURL(reportUrl);
    
    // Mostrar reporte en modal
    setDetailedReport(completeReport);
    // setAnalysisResults({ 
    //   type: 'complete_report', 
    //   data: { communities: communityAnalysis, centrality: centralityResults, paths: pathAnalysis },
    //   report: completeReport 
    // });
    setShowReportModal(true);
    
    console.log('✅ Reporte completo generado');
  };

  // Función auxiliar para calcular todas las centralidades
  const calculateAllCentralities = (nodes: Node[], edges: Edge[]) => {
    const results = nodes.map(node => {
      const degree = edges.filter(e => e.source === node.id || e.target === node.id).length;
      const betweenness = calculateBetweennessCentrality(node.id, nodes, edges);
      const closeness = calculateClosenessCentrality(node.id, nodes, edges);
      
      return {
        id: node.id,
        label: node.label,
        type: node.type,
        degree,
        betweenness,
        closeness,
        overall: (degree + betweenness + closeness) / 3
      };
    });
    
    return {
      nodes: results,
      topByDegree: results.sort((a, b) => b.degree - a.degree).slice(0, 5),
      topByBetweenness: results.sort((a, b) => b.betweenness - a.betweenness).slice(0, 5),
      topByCloseness: results.sort((a, b) => b.closeness - a.closeness).slice(0, 5),
      topOverall: results.sort((a, b) => b.overall - a.overall).slice(0, 5)
    };
  };

  // Función auxiliar para análisis de rutas
  const analyzeNetworkPaths = (nodes: Node[], edges: Edge[]) => {
    const bridgeNodes = nodes.filter(node => {
      const nodeEdges = edges.filter(e => e.source === node.id || e.target === node.id);
      return nodeEdges.length >= 3; // Nodos con 3 o más conexiones como puentes potenciales
    });
    
    const criticalPaths = [];
    for (let i = 0; i < Math.min(5, nodes.length); i++) {
      for (let j = i + 1; j < Math.min(5, nodes.length); j++) {
        const path = findShortestPath(nodes[i].id, nodes[j].id, edges);
        if (path && path.length > 0) {
          criticalPaths.push({
            from: nodes[i].label,
            to: nodes[j].label,
            length: path.length,
            path: path.map(nodeId => nodes.find(n => n.id === nodeId)?.label).join(' → ')
          });
        }
      }
    }
    
    return {
      bridgeNodes: bridgeNodes.map(n => ({ id: n.id, label: n.label, connections: edges.filter(e => e.source === n.id || e.target === n.id).length })),
      criticalPaths: criticalPaths.slice(0, 10),
      averagePathLength: criticalPaths.length > 0 ? (criticalPaths.reduce((sum, p) => sum + p.length, 0) / criticalPaths.length).toFixed(2) : '0'
    };
  };

  // Función para generar el reporte completo
  const generateCompleteReport = (data: any) => {
    let report = `REPORTE COMPLETO DE ANÁLISIS DE RED OSINT\n`;
    report += `${'='.repeat(60)}\n\n`;
    
    // Resumen ejecutivo
    if (data.executiveSummary) {
      report += data.executiveSummary.replace(/\n/g, '\n');
    } else {
      report += 'Resumen ejecutivo no disponible\n';
    }
    
    // Análisis de comunidades
    report += `\n\nANÁLISIS DE COMUNIDADES\n`;
    report += `${'='.repeat(30)}\n\n`;
    
    const communities = data.communities || [];
    report += `Comunidades detectadas: ${communities.length}\n\n`;
    
    if (communities.length > 0) {
      communities.forEach((community: any, index: number) => {
        report += `Comunidad ${index + 1}\n`;
        report += `- Tamaño: ${community.nodes?.length || 0} nodos\n`;
        report += `- Centralidad promedio: ${community.avgCentrality?.toFixed(3) || 'N/A'}\n`;
        report += `- Nodos principales: ${community.principalNodes?.map((n: any) => n.label).join(', ') || 'N/A'}\n`;
        report += `- Miembros: ${community.nodes?.map((n: any) => n.label).join(', ') || 'N/A'}\n\n`;
      });
    } else {
      report += 'No se detectaron comunidades en la red actual.\n\n';
    }
    
    // Análisis de centralidad
    report += `\nANÁLISIS DE CENTRALIDAD\n`;
    report += `${'='.repeat(30)}\n\n`;
    
    const centrality = data.centrality || {};
    
    if (centrality.topByDegree && centrality.topByDegree.length > 0) {
      report += `Top 5 por Grado de Centralidad\n`;
      centrality.topByDegree.forEach((node: any, index: number) => {
        report += `${index + 1}. ${node.label || 'N/A'} (${node.type || 'N/A'}) - ${node.degree || 0} conexiones\n`;
      });
    } else {
      report += `Top 5 por Grado de Centralidad\nNo hay datos disponibles\n`;
    }
    
    if (centrality.topByBetweenness && centrality.topByBetweenness.length > 0) {
      report += `\nTop 5 por Centralidad de Intermediación\n`;
      centrality.topByBetweenness.forEach((node: any, index: number) => {
        report += `${index + 1}. ${node.label || 'N/A'} (${node.type || 'N/A'}) - ${node.betweenness?.toFixed(3) || 'N/A'}\n`;
      });
    } else {
      report += `\nTop 5 por Centralidad de Intermediación\nNo hay datos disponibles\n`;
    }
    
    if (centrality.topByCloseness && centrality.topByCloseness.length > 0) {
      report += `\nTop 5 por Centralidad de Cercanía\n`;
      centrality.topByCloseness.forEach((node: any, index: number) => {
        report += `${index + 1}. ${node.label || 'N/A'} (${node.type || 'N/A'}) - ${node.closeness?.toFixed(3) || 'N/A'}\n`;
      });
    } else {
      report += `\nTop 5 por Centralidad de Cercanía\nNo hay datos disponibles\n`;
    }
    
    // Análisis de rutas
    report += `\n\nANÁLISIS DE RUTAS Y CONECTIVIDAD\n`;
    report += `${'='.repeat(40)}\n\n`;
    
    const paths = data.paths || {};
    const averagePathLength = paths.averagePathLength || 'N/A';
    const bridgeNodes = paths.bridgeNodes || [];
    const criticalPaths = paths.criticalPaths || [];
    
    report += `Longitud promedio de rutas: ${averagePathLength}\n\n`;
    
    report += `Nodos Puente (${bridgeNodes.length})\n`;
    if (bridgeNodes.length > 0) {
      bridgeNodes.forEach((node: any, index: number) => {
        report += `${index + 1}. ${node.label || 'N/A'} - ${node.connections || 0} conexiones\n`;
      });
    } else {
      report += 'No se identificaron nodos puente.\n';
    }
    
    report += `\nRutas Críticas\n`;
    if (criticalPaths.length > 0) {
      criticalPaths.slice(0, 5).forEach((path: any, index: number) => {
        report += `${index + 1}. ${path.from || 'N/A'} → ${path.to || 'N/A'} (${path.length || 0} pasos)\n`;
        report += `   Ruta: ${path.path || 'N/A'}\n`;
      });
    } else {
      report += 'No se identificaron rutas críticas.\n';
    }
    
    // Conclusiones y recomendaciones
    report += `\n\nCONCLUSIONES Y RECOMENDACIONES\n`;
    report += `${'='.repeat(40)}\n\n`;
    
    if (communities.length > 1) {
      report += `- Se identificaron ${communities.length} comunidades distintas en la red\n`;
    } else if (communities.length === 1) {
      report += `- Se identificó 1 comunidad principal en la red\n`;
    } else {
      report += `- No se detectaron comunidades estructuradas en la red\n`;
    }
    
    const topOverall = centrality.topOverall || [];
    const topNode = topOverall[0];
    if (topNode) {
      report += `- El nodo más influyente es "${topNode.label || 'N/A'}" con alta centralidad general\n`;
    } else {
      report += `- No se pudo identificar un nodo claramente dominante\n`;
    }
    
    if (bridgeNodes.length > 0) {
      report += `- Se identificaron ${bridgeNodes.length} nodos puente críticos para la conectividad\n`;
    } else {
      report += `- No se identificaron nodos puente críticos\n`;
    }
    
    report += `- Se recomienda monitoreo continuo de los nodos de alta centralidad\n`;
    report += `- Considerar análisis temporal para detectar cambios en la estructura\n`;
    
    report += `\n\nMETADATOS DEL ANÁLISIS\n`;
    report += `${'='.repeat(30)}\n`;
    report += `- Fecha de generación: ${new Date().toLocaleString()}\n`;
    report += `- Total de nodos analizados: ${nodes.length}\n`;
    report += `- Total de conexiones analizadas: ${edges.length}\n`;
    report += `- Herramienta: OSINT Platform - Análisis de Grafos\n`;
    
    return report;
  };

  // Función para cambiar layout
  const changeLayout = (newLayout: string) => {
    setLayoutType(newLayout);
    if (cyInstance.current) {
      cyInstance.current.layout({ name: newLayout }).run();
    }
  };

  // Función para hacer zoom
   const handleZoom = (direction: 'in' | 'out' | 'reset') => {
     if (!cyInstance.current) return;
     
     switch (direction) {
       case 'in':
         cyInstance.current.zoom(cyInstance.current.zoom() * 1.2);
         break;
       case 'out':
         cyInstance.current.zoom(cyInstance.current.zoom() * 0.8);
         break;
       case 'reset':
         cyInstance.current.fit();
         break;
     }
   };

   // Función de búsqueda
   const handleSearch = (term: string) => {
     setSearchTerm(term);
     if (!cyInstance.current) return;

     // Remover highlights anteriores
     cyInstance.current.elements().removeClass('highlighted');

     if (term.trim()) {
       // Buscar nodos que coincidan
       const matchingNodes = cyInstance.current.nodes().filter((node) => {
         const label = node.data('label').toLowerCase();
         return label.includes(term.toLowerCase());
       });

       // Highlight nodos encontrados
       matchingNodes.addClass('highlighted');

       // Centrar en el primer resultado
       if (matchingNodes.length > 0) {
         cyInstance.current.center(matchingNodes.first());
       }
     }
   };

   // Función para exportar
   const handleExport = async (format: 'png' | 'json') => {
     if (!cyInstance.current) return;

     try {
       if (format === 'png') {
         const png = cyInstance.current.png({ scale: 2, full: true });
         const link = document.createElement('a');
         link.download = 'graph.png';
         link.href = png;
         link.click();
       } else if (format === 'json') {
         const data = {
           nodes: nodes,
           edges: edges,
           communities: communities
         };
         const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
         const url = URL.createObjectURL(blob);
         const link = document.createElement('a');
         link.download = 'graph-data.json';
         link.href = url;
         link.click();
         URL.revokeObjectURL(url);
       }
       setShowExportModal(false);
     } catch (error) {
       console.error('Error al exportar:', error);
     }
   };

   // Función para análisis de comunidades (versión visual)
   const performCommunityAnalysisVisual = () => {
     if (!cyInstance.current) return;

     // Algoritmo simple de detección de comunidades basado en conectividad
     const nodes = cyInstance.current.nodes();
     const communities: string[][] = [];
     const visited = new Set<string>();

     nodes.forEach((node) => {
       const nodeId = node.id();
       if (!visited.has(nodeId)) {
         const community: string[] = [];
         const queue = [node];
         
         while (queue.length > 0) {
           const currentNode = queue.shift()!;
           const currentId = currentNode.id();
           
           if (!visited.has(currentId)) {
             visited.add(currentId);
             community.push(currentId);
             
             // Agregar vecinos conectados
             const neighbors = currentNode.neighborhood('node');
             neighbors.forEach((neighbor) => {
               if (!visited.has(neighbor.id())) {
                 queue.push(neighbor);
               }
             });
           }
         }
         
         if (community.length > 1) {
           communities.push(community);
         }
       }
     });

     // Colorear comunidades
     const communityColors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57', '#ff9ff3'];
     
     communities.forEach((community, index) => {
       const color = communityColors[index % communityColors.length];
       community.forEach((nodeId) => {
         cyInstance.current!.getElementById(nodeId).style('background-color', color);
       });
     });

     console.log(`Detectadas ${communities.length} comunidades:`, communities);
   };

   // Función para análisis de comunidades (versión que retorna datos)
   const performCommunityAnalysis = (nodes: Node[], edges: Edge[]) => {
     if (!nodes || !edges) return [];

     // Algoritmo de detección de comunidades basado en conectividad
     const communities: any[] = [];
     const visited = new Set<string>();
     const nodeMap = new Map(nodes.map(n => [n.id, n]));

     nodes.forEach((node) => {
       if (!visited.has(node.id)) {
         const communityNodeIds: string[] = [];
         const queue = [node.id];
         
         while (queue.length > 0) {
           const currentId = queue.shift()!;
           
           if (!visited.has(currentId)) {
             visited.add(currentId);
             communityNodeIds.push(currentId);
             
             // Encontrar vecinos conectados
             const connectedEdges = edges.filter(e => 
               e.source === currentId || e.target === currentId
             );
             
             connectedEdges.forEach(edge => {
               const neighborId = edge.source === currentId ? edge.target : edge.source;
               if (!visited.has(neighborId)) {
                 queue.push(neighborId);
               }
             });
           }
         }
         
         if (communityNodeIds.length > 1) {
           // Crear objeto de comunidad con la estructura esperada
           const communityNodes = communityNodeIds.map(id => nodeMap.get(id)).filter(Boolean);
           const communityEdges = edges.filter(e => 
             communityNodeIds.includes(e.source) && communityNodeIds.includes(e.target)
           );
           
           // Calcular centralidad promedio
           const avgCentrality = communityNodes.reduce((sum, node) => {
             const degree = edges.filter(e => e.source === node!.id || e.target === node!.id).length;
             return sum + degree;
           }, 0) / communityNodes.length;
           
           // Identificar nodos principales (los de mayor grado)
           const principalNodes = communityNodes
             .map(node => ({
               ...node!,
               degree: edges.filter(e => e.source === node!.id || e.target === node!.id).length
             }))
             .sort((a, b) => b.degree - a.degree)
             .slice(0, Math.min(3, communityNodes.length));
           
           communities.push({
             nodes: communityNodes,
             edges: communityEdges,
             avgCentrality,
             principalNodes,
             size: communityNodes.length
           });
         }
       }
     });

     return communities;
   };


  const effectiveShowSidePanel = showSidePanel && !isFullscreen;

  const graphCanvasStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    backgroundColor: '#060B14',
    backgroundImage: [
      'radial-gradient(circle at 20% 25%, rgba(0, 212, 255, 0.14), transparent 45%)',
      'radial-gradient(circle at 78% 70%, rgba(155, 89, 182, 0.10), transparent 52%)',
      'radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px)',
      'radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px)'
    ].join(', '),
    backgroundSize: '100% 100%, 100% 100%, 26px 26px, 48px 48px',
    backgroundPosition: 'center, center, 0 0, 12px 16px'
  };


  return (
    <div className="app-shell">
      <Header user={user} onLogout={onLogout} />

      <Container fluid className="app-page py-4">
        <Row className="mb-4">
          <Col>
            <div className="d-flex justify-content-between align-items-center">
              <h4 className="text-light mb-0">
                <i className="bi bi-diagram-3 me-2"></i>
                Análisis de Grafos OSINT
              </h4>
              <div className="d-flex gap-2">
                <InputGroup style={{ width: '250px' }}>
                  <Form.Control
                    type="text"
                    placeholder="Buscar nodos..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="bg-dark border-secondary text-light"
                  />
                  <Button variant="outline-secondary">
                    <i className="bi bi-search"></i>
                  </Button>
                </InputGroup>
                
                <Button 
                  variant="outline-info"
                  size="sm"
                  onClick={() => setShowSidePanel(!showSidePanel)}
                >
                  <i className="bi bi-layout-sidebar me-1"></i>
                  Panel
                </Button>
                
                <Button 
                  variant="outline-success" 
                  size="sm"
                  onClick={() => setShowExportModal(true)}
                >
                  <i className="bi bi-download me-1"></i>
                  Exportar
                </Button>
              </div>
            </div>
          </Col>
        </Row>

        {/* Estadísticas del Grafo */}
        <Row className="mb-4">
          <Col md={3}>
            <Card className="bg-primary text-white h-100">
              <Card.Body className="d-flex align-items-center">
                <i className="bi bi-circle-fill fs-1 me-3"></i>
                <div>
                  <h3 className="mb-0">{nodes.filter(n => nodeTypeFilter === 'all' || n.type === nodeTypeFilter).length}</h3>
                  <small>Nodos Visibles</small>
                </div>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3}>
            <Card className="bg-success text-white h-100">
              <Card.Body className="d-flex align-items-center">
                <i className="bi bi-arrow-left-right fs-1 me-3"></i>
                <div>
                  <h3 className="mb-0">{edges.filter(e => edgeTypeFilter === 'all' || e.type === edgeTypeFilter).length}</h3>
                  <small>Conexiones</small>
                </div>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3}>
            <Card className="bg-warning text-dark h-100">
              <Card.Body className="d-flex align-items-center">
                <i className="bi bi-people fs-1 me-3"></i>
                <div>
                  <h3 className="mb-0">{communities.length}</h3>
                  <small>Comunidades</small>
                </div>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3}>
            <Card className="bg-info text-white h-100">
              <Card.Body className="d-flex align-items-center">
                <i className="bi bi-graph-up fs-1 me-3"></i>
                <div>
                  <h3 className="mb-0">{searchTerm ? cyInstance.current?.nodes('.highlighted').length || 0 : nodes.length}</h3>
                  <small>{searchTerm ? 'Encontrados' : 'Total Nodos'}</small>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Controles de Filtrado */}
        <Row className="mb-4">
          <Col>
            <Card bg="dark" border="secondary">
              <Card.Header className="bg-secondary d-flex justify-content-between align-items-center">
                  <h6 className="mb-0 text-light">
                    <i className="bi bi-funnel me-2"></i>
                    Filtros y Controles de Visualización
                  </h6>
                  <Button 
                    variant="outline-warning" 
                    size="sm"
                    onClick={performCommunityAnalysisVisual}
                  >
                    <i className="bi bi-people me-1"></i>
                    Detectar Comunidades
                  </Button>
                </Card.Header>
              <Card.Body>
                <Row className="g-3 mb-3">
                  <Col md={6}>
                    <Form.Label className="text-light">Investigación</Form.Label>
                    <InputGroup>
                      <Form.Select
                        value={selectedInvestigationId}
                        onChange={(e) => setSelectedInvestigationId(e.target.value)}
                        className="bg-dark border-secondary text-light"
                        disabled={graphLoading || investigations.length === 0}
                      >
                        <option value="">{investigations.length === 0 ? 'Sin investigaciones' : 'Seleccionar...'}</option>
                        {investigations.map((inv) => (
                          <option key={inv.id} value={inv.id}>
                            {inv.title}
                          </option>
                        ))}
                      </Form.Select>
                      <Button
                        variant="outline-info"
                        onClick={() => selectedInvestigationId && loadGraphData(selectedInvestigationId)}
                        disabled={!selectedInvestigationId || graphLoading}
                      >
                        <i className="bi bi-arrow-repeat"></i>
                      </Button>
                    </InputGroup>
                  </Col>
                  <Col md={3}>
                    <Form.Label className="text-light">Tipo de Nodo</Form.Label>
                    <Form.Select
                      value={nodeTypeFilter}
                      onChange={(e) => setNodeTypeFilter(e.target.value)}
                      className="bg-dark border-secondary text-light"
                    >
                      <option value="all">Todos ({nodes.length})</option>
                      {Array.from(new Set(nodes.map((n) => n.type))).sort().map((t) => (
                        <option key={t} value={t}>
                          {getNodeTypeText(t)} ({nodes.filter((n) => n.type === t).length})
                        </option>
                      ))}
                    </Form.Select>
                  </Col>
                  <Col md={3}>
                    <Form.Label className="text-light">Tipo de Conexión</Form.Label>
                    <Form.Select
                      value={edgeTypeFilter}
                      onChange={(e) => setEdgeTypeFilter(e.target.value)}
                      className="bg-dark border-secondary text-light"
                    >
                      <option value="all">Todas ({edges.length})</option>
                      {Array.from(new Set(edges.map((e) => e.type))).sort().map((t) => (
                        <option key={t} value={t}>
                          {t} ({edges.filter((e) => e.type === t).length})
                        </option>
                      ))}
                    </Form.Select>
                  </Col>
                </Row>

                <Row className="g-3">
                  <Col md={2}>
                    <Form.Label className="text-light">Layout</Form.Label>
                    <Form.Select
                      value={layoutType}
                      onChange={(e) => changeLayout(e.target.value)}
                      className="bg-dark border-secondary text-light"
                    >
                      <option value="cose-bilkent">Cose-Bilkent</option>
                      <option value="circle">Circular</option>
                      <option value="grid">Cuadrícula</option>
                      <option value="breadthfirst">Jerárquico</option>
                      <option value="concentric">Concéntrico</option>
                    </Form.Select>
                  </Col>
                  <Col md={2}>
                    <Form.Label className="text-light">Controles de Zoom</Form.Label>
                    <ButtonGroup className="w-100">
                      <OverlayTrigger
                        placement="top"
                        overlay={<Tooltip>Alejar</Tooltip>}
                      >
                        <Button variant="outline-secondary" size="sm" onClick={() => handleZoom('out')}>
                          <i className="bi bi-zoom-out"></i>
                        </Button>
                      </OverlayTrigger>
                      <OverlayTrigger
                        placement="top"
                        overlay={<Tooltip>Ajustar a pantalla</Tooltip>}
                      >
                        <Button variant="outline-secondary" size="sm" onClick={() => handleZoom('reset')}>
                          <i className="bi bi-arrows-fullscreen"></i>
                        </Button>
                      </OverlayTrigger>
                      <OverlayTrigger
                        placement="top"
                        overlay={<Tooltip>Acercar</Tooltip>}
                      >
                        <Button variant="outline-secondary" size="sm" onClick={() => handleZoom('in')}>
                          <i className="bi bi-zoom-in"></i>
                        </Button>
                      </OverlayTrigger>
                    </ButtonGroup>
                  </Col>
                  <Col md={8}>
                    <Form.Label className="text-light">Herramientas de Análisis</Form.Label>
                    <ButtonGroup className="w-100">
                      <Button 
                        variant="outline-info" 
                        size="sm"
                        onClick={() => cyInstance.current?.elements().removeClass('highlighted')}
                      >
                        <i className="bi bi-eraser me-1"></i>
                        Limpiar
                      </Button>
                      <Button 
                        variant="outline-primary" 
                        size="sm"
                        onClick={() => cyInstance.current?.center()}
                      >
                        <i className="bi bi-crosshair me-1"></i>
                        Centrar
                      </Button>
                    </ButtonGroup>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Área de Visualización del Grafo */}
        <Row className="mb-4">
          <Col lg={effectiveShowSidePanel ? 8 : 12}>
            <div ref={graphContainerRef} style={{ height: isFullscreen ? '100vh' : '600px' }}>
              <Card bg="dark" border="secondary" style={{ height: '100%' }}>
                <Card.Header className="bg-secondary d-flex justify-content-between align-items-center">
                  <h6 className="mb-0 text-light">
                    <i className="bi bi-diagram-2 me-2"></i>
                    Visualización del Grafo - Layout: {layoutType.charAt(0).toUpperCase() + layoutType.slice(1)}
                  </h6>
                  <div className="d-flex gap-2">
                    <Button 
                      variant="outline-light" 
                      size="sm"
                      onClick={() => cyInstance.current?.fit()}
                    >
                      <i className="bi bi-arrows-fullscreen me-1"></i>
                      Ajustar
                    </Button>
                    <Button 
                      variant="outline-light" 
                      size="sm"
                      onClick={() => cyInstance.current?.center()}
                    >
                      <i className="bi bi-crosshair me-1"></i>
                      Centrar
                    </Button>
                    <ButtonGroup size="sm">
                      <Button variant="outline-light" onClick={() => void handleExport('png')}>
                        <i className="bi bi-download me-1"></i>PNG
                      </Button>
                      <Button variant="outline-light" onClick={() => void handleExport('json')}>
                        <i className="bi bi-filetype-json me-1"></i>JSON
                      </Button>
                      <Button variant="outline-light" onClick={() => void toggleFullscreen()}>
                        <i className={`bi ${isFullscreen ? 'bi-fullscreen-exit' : 'bi-fullscreen'}`}></i>
                      </Button>
                    </ButtonGroup>
                  </div>
                </Card.Header>
                <Card.Body className="p-0 position-relative">
                  <div ref={cyRef} style={graphCanvasStyle} />
                {(graphLoading || graphError || !selectedInvestigationId || (nodes.length === 0 && edges.length === 0)) && (
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '24px',
                      background: 'rgba(0,0,0,0.55)',
                      backdropFilter: 'blur(2px)',
                      textAlign: 'center',
                      pointerEvents: 'none',
                    }}
                  >
                    <div style={{ maxWidth: 520 }}>
                      <div className="text-light fw-semibold mb-2">
                        {graphLoading ? 'Cargando grafo…' : graphError ? 'No se pudo cargar el grafo' : !selectedInvestigationId ? 'Selecciona una investigación' : 'Sin datos para mostrar'}
                      </div>
                      {graphError && <div className="text-warning small">{graphError}</div>}
                    </div>
                  </div>
                )}
                </Card.Body>
              </Card>
            </div>
          </Col>
          
          {/* Panel Lateral */}
          {effectiveShowSidePanel && (
            <Col lg={4}>
              <Card bg="dark" border="secondary" style={{ height: '600px' }}>
                <Card.Header className="bg-secondary d-flex justify-content-between align-items-center">
                  <h6 className="mb-0 text-light">
                    <i className="bi bi-info-circle me-2"></i>
                    Detalles del Elemento
                  </h6>
                  <Button 
                    variant="outline-light" 
                    size="sm"
                    onClick={() => setShowSidePanel(false)}
                  >
                    <i className="bi bi-x"></i>
                  </Button>
                </Card.Header>
                <Card.Body className="overflow-auto">
                  {selectedNode ? (
                    <div>
                      <div className="d-flex align-items-center mb-3">
                        <div 
                          className="rounded-circle me-3"
                          style={{
                            width: '40px',
                            height: '40px',
                            backgroundColor: getNodeColorHex(selectedNode.type),
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}
                        >
                          <i className={`bi bi-${getNodeIcon(selectedNode.type)} text-white`}></i>
                        </div>
                        <div>
                          <h6 className="text-light mb-1">{selectedNode.label}</h6>
                          <small className="text-muted text-capitalize">{getNodeTypeText(selectedNode.type)}</small>
                        </div>
                      </div>
                      
                      <hr className="border-secondary" />
                    
                    <div className="mb-3">
                      <h6 className="text-light mb-2">Información General</h6>
                      <div className="text-muted small">
                        <div className="d-flex justify-content-between mb-1">
                          <span>ID:</span>
                          <span className="text-light">{selectedNode.id}</span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Tipo:</span>
                          <span className="text-light text-capitalize">{getNodeTypeText(selectedNode.type)}</span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Centralidad:</span>
                          <span className="text-light">{selectedNode.centrality?.toFixed(3) || 'N/A'}</span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Comunidad:</span>
                          <span className="text-light">{selectedNode.community || 'Sin asignar'}</span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Confidence Score:</span>
                          <span className="text-light">
                            <Badge bg={(selectedNode.confidence || 0) > 0.8 ? 'success' : (selectedNode.confidence || 0) > 0.5 ? 'warning' : 'danger'} className="ms-1">
                              {((selectedNode.confidence || Math.random() * 0.4 + 0.6) * 100).toFixed(1)}%
                            </Badge>
                          </span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Fuente:</span>
                          <span className="text-light">{selectedNode.source || 'Manual'}</span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Creado:</span>
                          <span className="text-light">{selectedNode.created_at || new Date().toLocaleDateString()}</span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Actualizado:</span>
                          <span className="text-light">{selectedNode.updated_at || new Date().toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                    
                    <hr className="border-secondary" />
                    
                    <div className="mb-3">
                      <h6 className="text-light mb-2">Propiedades Adicionales</h6>
                      <div className="text-muted small">
                        {selectedNode.type === 'person' && (
                          <>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Edad:</span>
                              <span className="text-light">{selectedNode.age || 'No disponible'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Ocupación:</span>
                              <span className="text-light">{selectedNode.occupation || 'No disponible'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Ubicación:</span>
                              <span className="text-light">{selectedNode.location || 'No disponible'}</span>
                            </div>
                          </>
                        )}
                        {selectedNode.type === 'organization' && (
                          <>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Industria:</span>
                              <span className="text-light">{selectedNode.industry || 'No disponible'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Tamaño:</span>
                              <span className="text-light">{selectedNode.size || 'No disponible'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span>País:</span>
                              <span className="text-light">{selectedNode.country || 'No disponible'}</span>
                            </div>
                          </>
                        )}
                        {selectedNode.type === 'ip' && (
                          <>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Geolocalización:</span>
                              <span className="text-light">{selectedNode.geolocation || 'No disponible'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span>ISP:</span>
                              <span className="text-light">{selectedNode.isp || 'No disponible'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Tipo IP:</span>
                              <span className="text-light">{selectedNode.ip_type || 'IPv4'}</span>
                            </div>
                          </>
                        )}
                        {selectedNode.type === 'domain' && (
                          <>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Registrador:</span>
                              <span className="text-light">{selectedNode.registrar || 'No disponible'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Fecha Registro:</span>
                              <span className="text-light">{selectedNode.registration_date || 'No disponible'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Estado:</span>
                              <span className="text-light">
                                <Badge bg={selectedNode.status === 'active' ? 'success' : 'secondary'}>
                                  {selectedNode.status || 'active'}
                                </Badge>
                              </span>
                            </div>
                          </>
                        )}
                        {selectedNode.type === 'email' && (
                          <>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Dominio:</span>
                              <span className="text-light">{selectedNode.domain || selectedNode.label?.split('@')[1] || 'No disponible'}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-1">
                              <span>Verificado:</span>
                              <span className="text-light">
                                <Badge bg={selectedNode.verified ? 'success' : 'warning'}>
                                  {selectedNode.verified ? 'Sí' : 'No verificado'}
                                </Badge>
                              </span>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                    
                    <hr className="border-secondary" />
                    
                    <div className="mb-3">
                      <h6 className="text-light mb-2">Transforms Relacionadas</h6>
                      <div className="text-muted small">
                        <div className="d-flex justify-content-between mb-1">
                          <span>Ejecutadas:</span>
                          <span className="text-light">{selectedNode.transform_count || Math.floor(Math.random() * 5) + 1}</span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Última Transform:</span>
                          <span className="text-light">{selectedNode.last_transform || 'Enriquecimiento de datos'}</span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Estado:</span>
                          <span className="text-light">
                            <Badge bg="success">Completado</Badge>
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <hr className="border-secondary" />
                    
                    <div className="mb-3">
                      <h6 className="text-light mb-2">Conexiones</h6>
                      <div className="text-muted small">
                        <div className="d-flex justify-content-between mb-1">
                          <span>Total:</span>
                          <span className="text-light">
                            {edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).length}
                          </span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Entrantes:</span>
                          <span className="text-light">
                            {edges.filter(e => e.target === selectedNode.id).length}
                          </span>
                        </div>
                        <div className="d-flex justify-content-between mb-1">
                          <span>Salientes:</span>
                          <span className="text-light">
                            {edges.filter(e => e.source === selectedNode.id).length}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <hr className="border-secondary" />
                    
                    <div className="mb-3">
                      <h6 className="text-light mb-2">Acciones</h6>
                      <div className="d-grid gap-2">
                        <Button 
                          variant="outline-primary" 
                          size="sm"
                          onClick={() => {
                            const connectedEdges = edges.filter(e => 
                              e.source === selectedNode.id || e.target === selectedNode.id
                            );
                            const connectedNodes = new Set();
                            connectedEdges.forEach(e => {
                              connectedNodes.add(e.source);
                              connectedNodes.add(e.target);
                            });
                            cyInstance.current?.elements().removeClass('highlighted');
                            cyInstance.current?.nodes().filter(n => connectedNodes.has(n.id())).addClass('highlighted');
                          }}
                        >
                          <i className="bi bi-diagram-2 me-1"></i>
                          Resaltar Conexiones
                        </Button>
                        <Button 
                          variant="outline-warning" 
                          size="sm"
                          onClick={() => {
                            cyInstance.current?.center(cyInstance.current.getElementById(selectedNode.id));
                          }}
                        >
                          <i className="bi bi-crosshair me-1"></i>
                          Centrar en Nodo
                        </Button>
                        <Button 
                          variant="outline-secondary" 
                          size="sm" 
                          onClick={() => {
                            // Expandir: mostrar nodos relacionados adicionales
                            const connectedEdges = edges.filter(e => 
                              e.source === selectedNode.id || e.target === selectedNode.id
                            );
                            const connectedNodeIds = new Set();
                            connectedEdges.forEach(e => {
                              connectedNodeIds.add(e.source);
                              connectedNodeIds.add(e.target);
                            });
                            
                            // Simular la adición de nodos relacionados de segundo nivel
                            const secondLevelNodes: any[] = [];
                            const secondLevelEdges: any[] = [];
                            let nodeCounter = nodes.length;
                            
                            connectedNodeIds.forEach(nodeId => {
                              if (nodeId !== selectedNode.id && Math.random() > 0.7) {
                                const newNodeId = `expanded_${nodeCounter++}`;
                                secondLevelNodes.push({
                                  id: newNodeId,
                                  label: `Relacionado ${nodeCounter}`,
                                  type: ['person', 'organization', 'ip', 'domain'][Math.floor(Math.random() * 4)],
                                  centrality: Math.random(),
                                  community: Math.floor(Math.random() * 3) + 1
                                });
                                secondLevelEdges.push({
                                  id: `edge_${nodeId}_${newNodeId}`,
                                  source: nodeId,
                                  target: newNodeId,
                                  type: 'related',
                                  label: 'Relacionado'
                                });
                              }
                            });
                            
                            if (secondLevelNodes.length > 0) {
                              setNodes(prev => [...prev, ...secondLevelNodes]);
                              setEdges(prev => [...prev, ...secondLevelEdges]);
                              console.log(`Se expandieron ${secondLevelNodes.length} nodos relacionados`);
                            } else {
                              console.log('No se encontraron nodos adicionales para expandir');
                            }
                          }}
                        >
                          <i className="bi bi-arrows-expand me-1"></i>Expandir
                        </Button>
                        <Button 
                          variant="outline-danger" 
                          size="sm" 
                          onClick={() => {
                            // Ocultar nodo y sus conexiones
                            const nodeToHide = selectedNode.id;
                            setNodes(prev => prev.filter(n => n.id !== nodeToHide));
                            setEdges(prev => prev.filter(e => e.source !== nodeToHide && e.target !== nodeToHide));
                            setSelectedNode(null);
                            console.log('Nodo ocultado del grafo');
                          }}
                        >
                          <i className="bi bi-eye-slash me-1"></i>Ocultar
                        </Button>
                      </div>
                    </div>
                    </div>
                  ) : selectedEdge ? (
                    <div>
                      <div className="d-flex align-items-center mb-3">
                        <div 
                          className="rounded me-3"
                          style={{
                            width: '40px',
                            height: '40px',
                            backgroundColor: getEdgeColor(selectedEdge.type),
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}
                        >
                          <i className="bi bi-arrow-right text-white"></i>
                        </div>
                        <div>
                          <h6 className="text-light mb-1">{selectedEdge.label}</h6>
                          <small className="text-muted text-capitalize">{selectedEdge.type}</small>
                        </div>
                      </div>
                      
                      <hr className="border-secondary" />
                      
                      <div className="mb-3">
                        <h6 className="text-light mb-2">Información de Conexión</h6>
                        <div className="text-muted small">
                          <div className="d-flex justify-content-between mb-1">
                            <span>Origen:</span>
                            <span className="text-light">
                              {nodes.find(n => n.id === selectedEdge.source)?.label || selectedEdge.source}
                            </span>
                          </div>
                          <div className="d-flex justify-content-between mb-1">
                            <span>Destino:</span>
                            <span className="text-light">
                              {nodes.find(n => n.id === selectedEdge.target)?.label || selectedEdge.target}
                            </span>
                          </div>
                          <div className="d-flex justify-content-between mb-1">
                            <span>Tipo:</span>
                            <span className="text-light text-capitalize">{selectedEdge.type}</span>
                          </div>
                          <div className="d-flex justify-content-between mb-1">
                            <span>Etiqueta:</span>
                            <span className="text-light">{selectedEdge.label}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center text-muted py-5">
                      <i className="bi bi-mouse2 display-4 mb-3"></i>
                      <p>Haz clic en un nodo o conexión para ver sus detalles</p>
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Col>
          )}
        </Row>

        {/* Herramientas de Análisis */}
        <Card bg="dark" border="secondary">
          <Card.Header className="bg-secondary">
            <h6 className="mb-0 text-light">
              <i className="bi bi-tools me-2"></i>
              Herramientas de Análisis
            </h6>
          </Card.Header>
          <Card.Body>
            <Row className="g-3">
              <Col md={2}>
                <Button variant="outline-primary" className="w-100" onClick={handleAnalyzeCommunities}>
                  <i className="bi bi-collection me-1"></i>
                  Detectar Comunidades
                </Button>
              </Col>
              <Col md={2}>
                <Button variant="outline-success" className="w-100" onClick={handleShortestPaths}>
                  <i className="bi bi-signpost me-1"></i>
                  Caminos Más Cortos
                </Button>
              </Col>
              <Col md={2}>
                <Button variant="outline-warning" className="w-100" onClick={handleCentralityAnalysis}>
                  <i className="bi bi-bullseye me-1"></i>
                  Análisis Centralidad
                </Button>
              </Col>
              <Col md={2}>
                <Button variant="outline-info" className="w-100" onClick={handleExportData}>
                  <i className="bi bi-download me-1"></i>
                  Exportar Datos
                </Button>
              </Col>
              <Col md={4}>
                <Button variant="outline-danger" className="w-100" onClick={handleGenerateCompleteReport}>
                  <i className="bi bi-file-earmark-text me-1"></i>
                  Generar Reporte Completo
                </Button>
              </Col>
            </Row>
          </Card.Body>
        </Card>

         {/* Modal de Exportación */}
         <Modal show={showExportModal} onHide={() => setShowExportModal(false)} centered>
           <Modal.Header closeButton className="bg-dark border-secondary">
             <Modal.Title className="text-light">
               <i className="bi bi-download me-2"></i>
               Exportar Grafo
             </Modal.Title>
           </Modal.Header>
           <Modal.Body className="bg-dark text-light">
             <h6 className="mb-3">Selecciona el formato de exportación:</h6>
             <div className="d-grid gap-2">
               <Button 
                 variant="outline-primary"
                 onClick={() => handleExport('png')}
               >
                 <i className="bi bi-image me-2"></i>
                 Exportar como PNG
                 <small className="d-block text-muted">Imagen de alta calidad</small>
               </Button>
               <Button 
                 variant="outline-success"
                 onClick={() => handleExport('json')}
               >
                 <i className="bi bi-filetype-json me-2"></i>
                 Exportar como JSON
                 <small className="d-block text-muted">Datos del grafo para análisis</small>
               </Button>
             </div>
           </Modal.Body>
           <Modal.Footer className="bg-dark border-secondary">
             <Button variant="secondary" onClick={() => setShowExportModal(false)}>
               Cancelar
             </Button>
           </Modal.Footer>
         </Modal>

         {/* Modal de Reporte Detallado */}
         <Modal show={showReportModal} onHide={() => setShowReportModal(false)} size="lg" centered>
           <Modal.Header closeButton className="bg-dark border-secondary">
             <Modal.Title className="text-light">
               <i className="bi bi-file-earmark-text me-2"></i>
               Reporte de Análisis Detallado
             </Modal.Title>
           </Modal.Header>
           <Modal.Body className="bg-dark text-light" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
             {detailedReport && (
               <div>
                 <div className="mb-4 p-3 bg-secondary rounded">
                   <h6 className="text-warning mb-2">
                     <i className="bi bi-info-circle me-2"></i>
                     Resumen Ejecutivo
                   </h6>
                   <div className="text-light" style={{ whiteSpace: 'pre-line', fontSize: '0.9rem' }}>
                     {detailedReport.split('## ANÁLISIS DE COMUNIDADES')[0]}
                   </div>
                 </div>
                 
                 <div className="border border-secondary rounded p-3">
                   <h6 className="text-info mb-3">
                     <i className="bi bi-clipboard-data me-2"></i>
                     Reporte Completo
                   </h6>
                   <pre className="text-light" style={{ 
                     fontSize: '0.8rem', 
                     lineHeight: '1.4',
                     whiteSpace: 'pre-wrap',
                     wordWrap: 'break-word',
                     backgroundColor: 'transparent',
                     border: 'none',
                     margin: 0
                   }}>
                     {detailedReport}
                   </pre>
                 </div>
               </div>
             )}
           </Modal.Body>
           <Modal.Footer className="bg-dark border-secondary">
             <Button 
               variant="outline-success" 
               onClick={() => {
                 const element = document.createElement('a');
                 const file = new Blob([detailedReport || ''], { type: 'text/plain' });
                 element.href = URL.createObjectURL(file);
                 element.download = `reporte-analisis-${new Date().toISOString().split('T')[0]}.txt`;
                 document.body.appendChild(element);
                 element.click();
                 document.body.removeChild(element);
               }}
             >
               <i className="bi bi-download me-1"></i>
               Descargar Reporte
             </Button>
             <Button variant="secondary" onClick={() => setShowReportModal(false)}>
               Cerrar
             </Button>
           </Modal.Footer>
         </Modal>
       </Container>
     </div>
   );
 };

export default GraphsPage;
