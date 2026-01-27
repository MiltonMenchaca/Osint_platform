import React from 'react';
import { Navbar, Nav, Button, Container, Dropdown, Badge } from 'react-bootstrap';
import { Link, useLocation } from 'react-router-dom';
import type { User } from '../types';

interface HeaderProps {
  user: User;
  onLogout: () => void;
  showWorkspaceToggle?: boolean;
  workspaceMode?: boolean;
  onWorkspaceToggle?: () => void;
}

const Header: React.FC<HeaderProps> = ({ 
  user, 
  onLogout, 
  showWorkspaceToggle = false, 
  workspaceMode = false, 
  onWorkspaceToggle 
}) => {
  const location = useLocation();
  const initials = (user.username || 'U').slice(0, 2).toUpperCase();

  return (
    <Navbar variant="dark" expand="lg" className="app-navbar" sticky="top">
      <Container fluid>
        <Navbar.Brand as={Link} to="/dashboard" className="d-flex align-items-center gap-2">
          <i className="bi bi-shield-lock me-2"></i>
          OSINT Platform
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link as={Link} to="/dashboard" active={location.pathname === '/dashboard'}>
              <i className="bi bi-house me-1"></i>
              Dashboard
            </Nav.Link>
            <Nav.Link as={Link} to="/investigations" active={location.pathname === '/investigations'}>
              <i className="bi bi-search me-1"></i>
              Investigaciones
            </Nav.Link>
            <Nav.Link as={Link} to="/graphs" active={location.pathname === '/graphs'}>
              <i className="bi bi-diagram-2 me-1"></i>
              Grafos
            </Nav.Link>
            <Nav.Link as={Link} to="/entities" active={location.pathname === '/entities'}>
              <i className="bi bi-diagram-3 me-1"></i>
              Entidades
            </Nav.Link>

          </Nav>
          <Nav className="ms-auto align-items-lg-center gap-2">
            {showWorkspaceToggle && onWorkspaceToggle && (
              <Button 
                variant="outline-warning" 
                size="sm" 
                className="me-lg-1"
                onClick={onWorkspaceToggle}
              >
                <i className={`bi bi-${workspaceMode ? 'table' : 'grid-3x3-gap'} me-1`}></i>
                {workspaceMode ? 'Vista Tabla' : 'Workspace'}
              </Button>
            )}
            <Dropdown align="end">
              <Dropdown.Toggle
                as={Button}
                variant="outline-light"
                size="sm"
                className="d-flex align-items-center gap-2"
              >
                <span className="app-avatar" aria-hidden="true">
                  {initials}
                </span>
                <span className="d-none d-md-inline">{user.username}</span>
                <Badge bg="secondary" className="d-none d-lg-inline">
                  {user.role}
                </Badge>
              </Dropdown.Toggle>
              <Dropdown.Menu variant="dark">
                <Dropdown.Header>Sesión</Dropdown.Header>
                <Dropdown.Item onClick={onLogout}>
                  <i className="bi bi-box-arrow-right me-2"></i>
                  Salir
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default Header
