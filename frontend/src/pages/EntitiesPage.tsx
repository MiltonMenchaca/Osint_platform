import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Button, Card, Table, Form, InputGroup, Badge, Dropdown, Pagination, Modal } from 'react-bootstrap';
import type { User, Entity } from '../types';
import Header from '../components/Header';
import { apiService } from '../services/api';

interface EntitiesPageProps {
  user: User;
  onLogout: () => void;
}

interface BackendEntityListItem {
  id: string;
  entity_type: string;
  value: string;
  confidence_score?: number;
  investigation_name?: string;
  created_at?: string;
  updated_at?: string;
  relationships_count?: number;
}

const EntitiesPage: React.FC<EntitiesPageProps> = ({ user, onLogout }) => {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [filteredEntities, setFilteredEntities] = useState<Entity[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const itemsPerPage = 5;

  useEffect(() => {
    loadEntities();
  }, []);

  useEffect(() => {
    filterEntities();
  }, [entities, searchTerm, typeFilter]);

  const filterEntities = () => {
    let filtered = [...entities];

    // Filtrar por término de búsqueda
    if (searchTerm) {
      filtered = filtered.filter(entity => 
        entity.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (entity.description && entity.description.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Filtrar por tipo
    if (typeFilter !== 'all') {
      filtered = filtered.filter(entity => entity.type === typeFilter);
    }

    setFilteredEntities(filtered);
    setCurrentPage(1); // Reset a la primera página cuando se filtra
  };

  const getCurrentPageItems = () => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredEntities.slice(startIndex, endIndex);
  };

  const totalPages = Math.ceil(filteredEntities.length / itemsPerPage);

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'person': return 'primary';
      case 'organization': return 'success';
      case 'ip': return 'warning';
      case 'domain': return 'info';
      case 'email': return 'secondary';
      default: return 'light';
    }
  };

  const getTypeText = (type: string) => {
    switch (type) {
      case 'person': return 'Persona';
      case 'organization': return 'Organización';
      case 'ip': return 'Dirección IP';
      case 'domain': return 'Dominio';
      case 'email': return 'Email';
      default: return type;
    }
  };

  const handleView = (entity: Entity) => {
    console.log('Ver entidad:', entity.name);
  };

  const handleEdit = (entity: Entity) => {
    console.log('Editar entidad:', entity.name);
  };

  const handleDelete = (entity: Entity) => {
    if (window.confirm(`¿Está seguro de que desea eliminar la entidad "${entity.name}"?`)) {
      console.warn('Eliminar entidad desde la vista global no está soportado sin investigación asociada:', entity.id);
    }
  };

  const loadEntities = async () => {
    console.log('🔄 Cargando entidades...');

    try {
      const res = await apiService.getEntities();
      if (!res.success) {
        console.error('💥 Error al cargar entidades:', res.message, res.errors);
        setEntities([]);
        return;
      }

      const payload: any = res.data;
      const items: BackendEntityListItem[] = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.results)
          ? payload.results
          : [];

      const mapped: Entity[] = items.map((e) => {
        const type = (e.entity_type || 'other') as Entity['type'];
        return {
          id: e.id,
          name: e.value,
          type,
          description: '',
          properties: {
            confidence_score: e.confidence_score,
            investigation_name: e.investigation_name,
            relationships_count: e.relationships_count,
          },
          value: e.value,
          created_at: e.created_at,
          updated_at: e.updated_at,
          createdAt: e.created_at,
          updatedAt: e.updated_at,
        };
      });

      setEntities(mapped);
      console.log('✅ Entidades cargadas correctamente');
      
    } catch (err) {
      console.error('💥 Error al cargar entidades:', err);
    }
  };

  return (
    <div className="app-shell">
      <Header user={user} onLogout={onLogout} />

      <Container fluid className="app-page py-4">
        <Row className="mb-4">
          <Col>
            <h4 className="text-light mb-3">
              <i className="bi bi-diagram-3 me-2"></i>
              Entidades
            </h4>
          </Col>
        </Row>

        {/* Estadísticas */}
        <Row className="mb-4">
          <Col md={3}>
            <Card border="primary" className="text-center">
              <Card.Body>
                <i className="bi bi-diagram-3 text-primary" style={{ fontSize: '2rem' }}></i>
                <h5 className="text-light mt-2">{entities.length}</h5>
                <p className="text-muted mb-0">Total Entidades</p>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3}>
            <Card border="success" className="text-center">
              <Card.Body>
                <i className="bi bi-people text-success" style={{ fontSize: '2rem' }}></i>
                <h5 className="text-light mt-2">{entities.filter(e => e.type === 'person').length}</h5>
                <p className="text-muted mb-0">Personas</p>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3}>
            <Card border="warning" className="text-center">
              <Card.Body>
                <i className="bi bi-building text-warning" style={{ fontSize: '2rem' }}></i>
                <h5 className="text-light mt-2">{entities.filter(e => e.type === 'organization').length}</h5>
                <p className="text-muted mb-0">Organizaciones</p>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3}>
            <Card border="info" className="text-center">
              <Card.Body>
                <i className="bi bi-globe text-info" style={{ fontSize: '2rem' }}></i>
                <h5 className="text-light mt-2">{entities.filter(e => e.type === 'ip' || e.type === 'domain').length}</h5>
                <p className="text-muted mb-0">Red/Dominios</p>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Filtros y Búsqueda */}
        <Row className="mb-4">
          <Col>
            <Card bg="dark" border="secondary">
              <Card.Body>
                <Row className="g-3">
                  <Col md={4}>
                    <InputGroup>
                      <InputGroup.Text className="bg-secondary border-secondary text-light">
                        <i className="bi bi-search"></i>
                      </InputGroup.Text>
                      <Form.Control
                        type="text"
                        placeholder="Buscar entidades..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="bg-dark border-secondary text-light"
                      />
                    </InputGroup>
                  </Col>
                  <Col md={4}>
                    <Form.Select
                      value={typeFilter}
                      onChange={(e) => setTypeFilter(e.target.value)}
                      className="bg-dark border-secondary text-light"
                    >
                      <option value="all">Todos los tipos</option>
                      <option value="person">Persona</option>
                      <option value="organization">Organización</option>
                      <option value="ip">Dirección IP</option>
                      <option value="domain">Dominio</option>
                      <option value="email">Email</option>
                    </Form.Select>
                  </Col>
                  <Col md={4}>
                    <Button variant="primary" className="w-100" onClick={() => setShowModal(true)}>
                      <i className="bi bi-plus-circle me-1"></i>
                      Nueva Entidad
                    </Button>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Tabla de Entidades */}
        <Row>
          <Col>
            <Card bg="dark" border="secondary">
              <Card.Body className="p-0">
                <Table responsive hover variant="dark" className="mb-0">
                  <thead className="bg-secondary">
                    <tr>
                      <th>ID</th>
                      <th>Nombre</th>
                      <th>Tipo</th>
                      <th>Descripción</th>
                      <th>Propiedades</th>
                      <th>Fecha Creación</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getCurrentPageItems().map((entity) => (
                      <tr key={entity.id}>
                        <td className="text-muted">#{entity.id}</td>
                        <td className="fw-bold">{entity.name}</td>
                        <td>
                          <Badge bg={getTypeColor(entity.type)}>
                            {getTypeText(entity.type)}
                          </Badge>
                        </td>
                        <td>
                          <div className="text-truncate" style={{ maxWidth: '200px' }}>
                            {entity.description || 'Sin descripción'}
                          </div>
                        </td>
                        <td>
                          <small className="text-muted">
                            {Object.keys(entity.properties).length} propiedades
                          </small>
                        </td>
                        <td className="text-muted">
                          {entity.createdAt ? new Date(entity.createdAt).toLocaleDateString('es-ES') : 'N/A'}
                        </td>
                        <td>
                          <Dropdown>
                            <Dropdown.Toggle variant="outline-secondary" size="sm">
                              <i className="bi bi-three-dots"></i>
                            </Dropdown.Toggle>
                            <Dropdown.Menu variant="dark">
                              <Dropdown.Item onClick={() => handleView(entity)}>
                                <i className="bi bi-eye me-2"></i>Ver
                              </Dropdown.Item>
                              <Dropdown.Item onClick={() => handleEdit(entity)}>
                                <i className="bi bi-pencil me-2"></i>Editar
                              </Dropdown.Item>
                              <Dropdown.Divider />
                              <Dropdown.Item className="text-danger" onClick={() => handleDelete(entity)}>
                                <i className="bi bi-trash me-2"></i>Eliminar
                              </Dropdown.Item>
                            </Dropdown.Menu>
                          </Dropdown>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Paginación */}
        {totalPages > 1 && (
          <Row className="mt-4">
            <Col className="d-flex justify-content-center">
              <Pagination>
                <Pagination.Prev 
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(currentPage - 1)}
                />
                {[...Array(totalPages)].map((_, index) => (
                  <Pagination.Item
                    key={index + 1}
                    active={index + 1 === currentPage}
                    onClick={() => setCurrentPage(index + 1)}
                  >
                    {index + 1}
                  </Pagination.Item>
                ))}
                <Pagination.Next 
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(currentPage + 1)}
                />
              </Pagination>
            </Col>
          </Row>
        )}

        {/* Modal para Nueva Entidad */}
        <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" centered>
          <Modal.Header closeButton className="bg-dark border-secondary">
            <Modal.Title className="text-light">
              <i className="bi bi-plus-circle me-2"></i>
              Nueva Entidad
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className="bg-dark">
            <Form>
              <Row className="g-3">
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="text-light">Nombre</Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="Ingrese el nombre de la entidad"
                      className="bg-dark border-secondary text-light"
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">Tipo</Form.Label>
                    <Form.Select className="bg-dark border-secondary text-light">
                      <option value="person">Persona</option>
                      <option value="organization">Organización</option>
                      <option value="ip">Dirección IP</option>
                      <option value="domain">Dominio</option>
                      <option value="email">Email</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label className="text-light">Estado</Form.Label>
                    <Form.Select className="bg-dark border-secondary text-light">
                      <option value="active">Activo</option>
                      <option value="inactive">Inactivo</option>
                      <option value="suspicious">Sospechoso</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label className="text-light">Descripción</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={3}
                      placeholder="Describa la entidad y su relevancia"
                      className="bg-dark border-secondary text-light"
                    />
                  </Form.Group>
                </Col>
              </Row>
            </Form>
          </Modal.Body>
          <Modal.Footer className="bg-dark border-secondary">
            <Button variant="secondary" onClick={() => setShowModal(false)}>
              Cancelar
            </Button>
            <Button variant="primary" onClick={() => setShowModal(false)}>
              <i className="bi bi-check-circle me-1"></i>
              Crear Entidad
            </Button>
          </Modal.Footer>
        </Modal>
      </Container>
    </div>
  );
};

export default EntitiesPage;
