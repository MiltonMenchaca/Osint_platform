import React, { useState } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import type { LoginCredentials } from '../types';
import apiService from '../services/api';

interface LoginProps {
  onLoginSuccess: () => void;
}

const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [credentials, setCredentials] = useState<LoginCredentials>({
    username: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setCredentials(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.login(credentials);
      
      if (response.success) {
        // Llamar al callback para actualizar el estado de autenticación
        onLoginSuccess();
      } else {
        setError(response.message || 'Error al iniciar sesión');
      }
    } catch (err) {
      console.error('💥 Error en login:', err);
      setError('Error de conexión. Por favor, intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const fillTestCredentials = () => {
    setCredentials({
      username: 'testadmin',
      password: 'admin123'
    });
  };

  return (
    <Container fluid className="app-shell d-flex align-items-center justify-content-center">
      <Row className="w-100 justify-content-center">
        <Col xs={12} sm={8} md={6} lg={4} xl={3}>
          <Card className="shadow-lg border-0 text-light">
            <Card.Header className="bg-primary text-white text-center py-4 border-0">
              <div className="mb-2">
                <i className="bi bi-shield-lock" style={{fontSize: '2.5rem'}}></i>
              </div>
              <h3 className="mb-0 fw-bold">
                OSINT Platform
              </h3>
              <small className="opacity-75">Intelligence & Analysis</small>
            </Card.Header>
            <Card.Body className="p-4">
              <Form onSubmit={handleSubmit}>
                <div className="text-center mb-4">
                  <h5 className="text-muted">Iniciar Sesión</h5>
                </div>

                {/* Credenciales de prueba */}
                <Alert variant="info" className="mb-3">
                  <div className="d-flex justify-content-between align-items-center">
                    <div>
                      <small className="fw-bold">Credenciales de prueba:</small><br/>
                      <small>Usuario: <code>testadmin</code></small><br/>
                      <small>Contraseña: <code>admin123</code></small>
                    </div>
                    <Button 
                      variant="outline-primary" 
                      size="sm"
                      onClick={fillTestCredentials}
                      disabled={loading}
                    >
                      <i className="bi bi-clipboard me-1"></i>
                      Usar
                    </Button>
                  </div>
                </Alert>

                {error && (
                  <Alert variant="danger" className="mb-3">
                    <i className="bi bi-exclamation-triangle me-2"></i>
                    {error}
                  </Alert>
                )}

                <Form.Group className="mb-3">
                  <Form.Label className="text-light fw-semibold">
                    <i className="bi bi-person me-2 text-primary"></i>
                    Usuario
                  </Form.Label>
                  <Form.Control
                    type="text"
                    name="username"
                    value={credentials.username}
                    onChange={handleInputChange}
                    placeholder="Ingresa tu usuario"
                    required
                    disabled={loading}
                    className="form-control-lg bg-secondary text-light border-secondary"
                    style={{borderRadius: '8px'}}
                  />
                </Form.Group>

                <Form.Group className="mb-4">
                  <Form.Label className="text-light fw-semibold">
                    <i className="bi bi-lock me-2 text-primary"></i>
                    Contraseña
                  </Form.Label>
                  <Form.Control
                    type="password"
                    name="password"
                    value={credentials.password}
                    onChange={handleInputChange}
                    placeholder="Ingresa tu contraseña"
                    required
                    disabled={loading}
                    className="form-control-lg bg-secondary text-light border-secondary"
                    style={{borderRadius: '8px'}}
                  />
                </Form.Group>

                <div className="d-grid">
                  <Button
                    variant="primary"
                    type="submit"
                    disabled={loading || !credentials.username || !credentials.password}
                    size="lg"
                    className="fw-semibold"
                    style={{borderRadius: '8px', padding: '12px'}}
                  >
                    {loading ? (
                      <>
                        <Spinner
                          as="span"
                          animation="border"
                          size="sm"
                          role="status"
                          aria-hidden="true"
                          className="me-2"
                        />
                        Iniciando sesión...
                      </>
                    ) : (
                      <>
                        <i className="bi bi-box-arrow-in-right me-2"></i>
                        Iniciar Sesión
                      </>
                    )}
                  </Button>
                </div>
              </Form>
            </Card.Body>
            <Card.Footer className="text-center text-light py-3 border-0">
              <small className="opacity-75">
                <i className="bi bi-info-circle me-1 text-primary"></i>
                Plataforma de Inteligencia de Fuentes Abiertas
              </small>
            </Card.Footer>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Login;
