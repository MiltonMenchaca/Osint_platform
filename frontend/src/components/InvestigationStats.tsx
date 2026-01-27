import React from 'react';
import { Card, Row, Col } from 'react-bootstrap';
import type { Investigation } from '../types';

interface InvestigationStatsProps {
  investigations: Investigation[];
  className?: string;
}

const InvestigationStats: React.FC<InvestigationStatsProps> = ({ investigations, className = '' }) => {
  // Calcular estadísticas básicas
  const total = investigations.length;
  const active = investigations.filter(inv => inv.status === 'active').length;
  const completed = investigations.filter(inv => inv.status === 'completed').length;
  const archived = investigations.filter(inv => inv.status === 'archived').length;
  
  const highPriority = investigations.filter(inv => inv.priority === 'high').length;
  const mediumPriority = investigations.filter(inv => inv.priority === 'medium').length;
  const lowPriority = investigations.filter(inv => inv.priority === 'low').length;

  return (
    <div className={`mb-4 ${className}`}>
      <h5 className="text-light mb-3">
        <i className="bi bi-bar-chart me-2"></i>
        Estadísticas de Investigaciones
      </h5>
      
      <Row className="g-3">
        {/* Estadísticas por Estado */}
        <Col md={3}>
          <Card bg="primary" text="white" className="h-100">
            <Card.Body className="text-center">
              <i className="bi bi-search" style={{ fontSize: '2rem' }}></i>
              <Card.Title className="mt-2">{total}</Card.Title>
              <Card.Text>Total</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={3}>
          <Card bg="success" text="white" className="h-100">
            <Card.Body className="text-center">
              <i className="bi bi-play-circle" style={{ fontSize: '2rem' }}></i>
              <Card.Title className="mt-2">{active}</Card.Title>
              <Card.Text>Activas</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={3}>
          <Card bg="info" text="white" className="h-100">
            <Card.Body className="text-center">
              <i className="bi bi-check-circle" style={{ fontSize: '2rem' }}></i>
              <Card.Title className="mt-2">{completed}</Card.Title>
              <Card.Text>Completadas</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={3}>
          <Card bg="secondary" text="white" className="h-100">
            <Card.Body className="text-center">
              <i className="bi bi-archive" style={{ fontSize: '2rem' }}></i>
              <Card.Title className="mt-2">{archived}</Card.Title>
              <Card.Text>Archivadas</Card.Text>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      <Row className="g-3 mt-2">
        {/* Estadísticas por Prioridad */}
        <Col md={4}>
          <Card bg="danger" text="white" className="h-100">
            <Card.Body className="text-center">
              <i className="bi bi-exclamation-triangle" style={{ fontSize: '1.5rem' }}></i>
              <Card.Title className="mt-2">{highPriority}</Card.Title>
              <Card.Text>Alta Prioridad</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={4}>
          <Card bg="warning" text="white" className="h-100">
            <Card.Body className="text-center">
              <i className="bi bi-dash-circle" style={{ fontSize: '1.5rem' }}></i>
              <Card.Title className="mt-2">{mediumPriority}</Card.Title>
              <Card.Text>Media Prioridad</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={4}>
          <Card bg="light" text="dark" className="h-100">
            <Card.Body className="text-center">
              <i className="bi bi-circle" style={{ fontSize: '1.5rem' }}></i>
              <Card.Title className="mt-2">{lowPriority}</Card.Title>
              <Card.Text>Baja Prioridad</Card.Text>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default InvestigationStats;