import React, { useEffect, useMemo, useState } from 'react';
import { Container, Row, Col, Card, Alert, Spinner, Badge, ProgressBar } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import type { User, DashboardStats } from '../../../types';
import apiService from '../../../services/api';
import Header from '../../../shared/components/Header';
import CyberMapBackground from '../../../shared/components/CyberMapBackground';

interface ExtendedDashboardStats extends DashboardStats {
  investigationsByStatus: { [key: string]: number };
  investigationsByPriority: { [key: string]: number };
  entitiesByType: { [key: string]: number };
  systemHealth: {
    cpu: number;
    memory: number;
    storage: number;
  };
  monthlyTrends: {
    investigations: number[];
    entities: number[];
  };
}

interface DashboardProps {
  user: User;
  onLogout: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({ user, onLogout }) => {
  const [stats, setStats] = useState<ExtendedDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const kpi = useMemo(() => {
    const total = stats?.totalInvestigations || 0;
    const active = stats?.activeInvestigations || 0;
    const entities = stats?.totalEntities || 0;
    const pulse = Math.max(1, Math.round((active * 9 + entities / 10) / 4));
    const risk = Math.min(99, Math.max(5, Math.round((active / Math.max(1, total)) * 100)));
    return { pulse, risk };
  }, [stats]);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getUserStats();
      if (!response.success || !response.data) {
        throw new Error(response.message || 'No se pudieron cargar las estadísticas');
      }

      const investigations = response.data?.investigations ?? {};
      const investigationsByStatus = investigations?.by_status ?? {};
      const executions = response.data?.executions ?? {};
      const entities = response.data?.entities ?? {};
      const entitiesByType = entities?.by_type ?? {};

      const mappedStats: ExtendedDashboardStats = {
        totalInvestigations: Number(investigations?.total ?? 0),
        activeInvestigations: Number(investigationsByStatus?.active ?? 0),
        completedInvestigations: Number(investigationsByStatus?.completed ?? 0),
        totalEntities: Number(entities?.total ?? 0),
        recentActivity: Number(investigations?.recent ?? 0) + Number(executions?.recent ?? 0),
        investigationsByStatus,
        investigationsByPriority: {},
        entitiesByType,
        systemHealth: { cpu: 0, memory: 0, storage: 0 },
        monthlyTrends: { investigations: [], entities: [] }
      };

      setStats(mappedStats);
    } catch {
      setError('Error al cargar las estadísticas del dashboard');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      active: 'success',
      completed: 'primary',
      archived: 'secondary'
    };
    return variants[status] || 'secondary';
  };

  const getPriorityBadge = (priority: string) => {
    const variants: Record<string, string> = {
      low: 'success',
      medium: 'warning',
      high: 'danger',
      critical: 'danger'
    };
    return variants[priority] || 'secondary';
  };

  return (
    <div className="cybermap-shell">
      <CyberMapBackground />
      <Header user={user} onLogout={onLogout} />

      <Container fluid className="app-page py-3 cybermap-dashboard">
        {error && (
          <Alert variant="danger" className="mb-4">
            <i className="bi bi-exclamation-triangle me-2"></i>
            {error}
          </Alert>
        )}

        {loading ? (
          <div className="text-center py-5">
            <Spinner animation="border" variant="primary" />
            <p className="text-muted mt-2">Cargando dashboard...</p>
          </div>
        ) : (
          <Row className="g-2 justify-content-between align-items-start">
            <Col xl={3} lg={4}>
              <div className="cybermap-side cybermap-side--left">
                <Card className="cybermap-panel">
                  <Card.Header className="mission-header">
                    <div className="mission-overline">SYSTEM STATUS</div>
                    <div className="mission-title">OP: CYBER WATCH</div>
                    <div className="mission-badge">Phase: Active Monitoring</div>
                  </Card.Header>
                  <Card.Body>
                    <div className="tactical-data-list">
                      <div className="tactical-data-row">
                        <span className="tactical-data-label">Pulse Rate</span>
                        <span className="tactical-data-value">{kpi.pulse} bpm</span>
                      </div>
                      <div className="tactical-data-row">
                        <span className="tactical-data-label">Risk Level</span>
                        <span className="tactical-data-value">{kpi.risk}%</span>
                      </div>
                      <div className="tactical-data-row">
                        <span className="tactical-data-label">Active Ops</span>
                        <span className="tactical-data-value">{stats?.totalInvestigations || 0}</span>
                      </div>
                      <div className="tactical-data-row">
                        <span className="tactical-data-label">Entities</span>
                        <span className="tactical-data-value">{stats?.totalEntities || 0}</span>
                      </div>
                      <div className="tactical-data-row">
                        <span className="tactical-data-label">Sys Load</span>
                        <span className="tactical-data-value">12/100</span>
                      </div>
                    </div>
                  </Card.Body>
                </Card>

                <Card className="cybermap-panel">
                  <Card.Header>
                    <div className="fw-semibold">
                      <i className="bi bi-lightning me-2"></i>
                      Acciones
                    </div>
                  </Card.Header>
                  <Card.Body className="p-2">
                    <div className="tactical-grid">
                      <Link to="/investigations" className="tactical-btn tactical-btn--primary">
                        <div className="tactical-btn__icon">
                          <i className="bi bi-search"></i>
                        </div>
                        <div className="tactical-btn__label">Nueva Inv.</div>
                        <div className="tactical-btn__corner"></div>
                      </Link>
                      
                      <Link to="/entities" className="tactical-btn tactical-btn--info">
                        <div className="tactical-btn__icon">
                          <i className="bi bi-diagram-3"></i>
                        </div>
                        <div className="tactical-btn__label">Entidades</div>
                        <div className="tactical-btn__corner"></div>
                      </Link>
                      
                      <Link to="/graphs" className="tactical-btn tactical-btn--warning">
                        <div className="tactical-btn__icon">
                          <i className="bi bi-diagram-2"></i>
                        </div>
                        <div className="tactical-btn__label">Grafos</div>
                        <div className="tactical-btn__corner"></div>
                      </Link>
                      
                      <button 
                        className="tactical-btn tactical-btn--secondary" 
                        onClick={loadDashboardData} 
                        disabled={loading}
                      >
                        <div className="tactical-btn__icon">
                          <i className="bi bi-arrow-clockwise"></i>
                        </div>
                        <div className="tactical-btn__label">Actualizar</div>
                        <div className="tactical-btn__corner"></div>
                      </button>
                    </div>
                  </Card.Body>
                </Card>
              </div>
            </Col>

            <Col xl={3} lg={4} className="ms-xl-auto cybermap-right">
              <div className="cybermap-side cybermap-side--right">
                <Card className="cybermap-panel">
                  <Card.Header>
                    <div className="fw-semibold">
                      <i className="bi bi-pie-chart me-2"></i>
                      Investigaciones por Estado
                    </div>
                  </Card.Header>
                  <Card.Body>
                    {Object.keys(stats?.investigationsByStatus || {}).length === 0 ? (
                      <div className="text-muted small">Sin datos</div>
                    ) : (
                      Object.entries(stats?.investigationsByStatus || {}).map(([status, count]) => {
                        const total = stats?.totalInvestigations || 1;
                        const percentage = Math.round((count / total) * 100);
                        return (
                          <div key={status} className="mb-1">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <span className="text-capitalize">
                                <Badge bg={getStatusBadge(status)} className="me-2">
                                  {status === 'active' ? 'Activo' :
                                    status === 'completed' ? 'Completado' :
                                      status === 'archived' ? 'Archivado' : 'Pendiente'}
                                </Badge>
                                {count}
                              </span>
                              <small className="text-muted">{percentage}%</small>
                            </div>
                            <ProgressBar variant={getStatusBadge(status)} now={percentage} style={{ height: '5px' }} />
                          </div>
                        );
                      })
                    )}
                  </Card.Body>
                </Card>

                <Card className="cybermap-panel">
                  <Card.Header>
                    <div className="fw-semibold">
                      <i className="bi bi-exclamation-triangle me-2"></i>
                      Investigaciones por Prioridad
                    </div>
                  </Card.Header>
                  <Card.Body>
                    {Object.keys(stats?.investigationsByPriority || {}).length === 0 ? (
                      <div className="text-muted small">No disponible</div>
                    ) : (
                      Object.entries(stats?.investigationsByPriority || {}).map(([priority, count]) => {
                        const total = stats?.totalInvestigations || 1;
                        const percentage = Math.round((count / total) * 100);
                        return (
                          <div key={priority} className="mb-1">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <span className="text-capitalize">
                                <Badge bg={getPriorityBadge(priority)} className="me-2">
                                  {priority === 'critical' ? 'Crítica' :
                                    priority === 'high' ? 'Alta' :
                                      priority === 'medium' ? 'Media' : 'Baja'}
                                </Badge>
                                {count}
                              </span>
                              <small className="text-muted">{percentage}%</small>
                            </div>
                            <ProgressBar variant={getPriorityBadge(priority)} now={percentage} style={{ height: '5px' }} />
                          </div>
                        );
                      })
                    )}
                  </Card.Body>
                </Card>
              </div>
            </Col>
          </Row>
        )}
      </Container>
    </div>
  );
};

export default Dashboard;
