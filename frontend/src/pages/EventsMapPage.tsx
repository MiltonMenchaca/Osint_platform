import { lazy, Suspense, useMemo, useState } from 'react';
import { Container, Row, Col, Card, Badge, Spinner } from 'react-bootstrap';
import type { User } from '../types';
import Header from '../components/Header';

const ProEventMap = lazy(() => import('../components/ProEventMap'));

type EventSeverity = 'low' | 'medium' | 'high' | 'critical';

interface EventsMapPageProps {
  user: User;
  onLogout: () => void;
}

const EventsMapPage = ({ user, onLogout }: EventsMapPageProps) => {
  const [minSeverity, setMinSeverity] = useState<EventSeverity>('medium');
  const proLabel = useMemo(() => `Pro · ${minSeverity}+`, [minSeverity]);

  return (
    <div className="app-shell">
      <Header user={user} onLogout={onLogout} />

      <Container fluid className="app-page py-4">
        <Row className="align-items-center mb-3">
          <Col>
            <div className="d-flex align-items-center gap-2 flex-wrap">
              <h4 className="text-light mb-0">
                <i className="bi bi-globe2 me-2"></i>
                Mapa de Eventos
              </h4>
              <Badge bg="secondary">{proLabel}</Badge>
            </div>
            <div className="text-muted small mt-1">
              Vista Pro con zoom/pan real y capa de eventos.
            </div>
          </Col>
        </Row>

        <Row className="g-4">
          <Col lg={12}>
            <Card>
              <Card.Header className="d-flex align-items-center justify-content-between flex-wrap gap-2">
                <div className="fw-semibold">
                  <i className="bi bi-broadcast me-2"></i>
                  Telemetría geográfica
                </div>
              </Card.Header>
              <Card.Body>
                <Suspense
                  fallback={
                    <div
                      className="d-flex align-items-center justify-content-center rounded-3 border border-dark-700"
                      style={{ height: 640, background: 'rgba(255,255,255,0.02)' }}
                    >
                      <div className="text-center">
                        <Spinner animation="border" variant="primary" />
                        <div className="text-muted mt-2">Cargando mapa Pro…</div>
                      </div>
                    </div>
                  }
                >
                  <ProEventMap height={640} minSeverity={minSeverity} onMinSeverityChange={setMinSeverity} />
                </Suspense>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default EventsMapPage;
