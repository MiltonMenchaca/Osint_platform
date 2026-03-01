import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Button, Card, Table, Form, InputGroup, Badge, Dropdown, Pagination, Modal, Alert } from 'react-bootstrap';
import Swal from 'sweetalert2';
import type { User, Entity } from '../types';
import Header from '../shared/components/Header';
import { apiService } from '../services/api';

interface EntitiesPageProps {
  user: User;
  onLogout: () => void;
}

const EntitiesPage: React.FC<EntitiesPageProps> = ({ user, onLogout }) => {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [filteredEntities, setFilteredEntities] = useState<Entity[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [investigationOptions, setInvestigationOptions] = useState<{ id: string; name: string }[]>([]);
  const [formEntity, setFormEntity] = useState<{
    investigationId: string;
    name: string;
    type: Entity['type'];
    value: string;
    description: string;
    propertiesText: string;
  }>({
    investigationId: '',
    name: '',
    type: 'domain',
    value: '',
    description: '',
    propertiesText: '{}',
  });
  const itemsPerPage = 5;

  useEffect(() => {
    loadEntities();
    loadInvestigations();
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
    const open = async () => {
      const investigationId = entity.investigationId ?? (typeof entity.investigation === 'string' ? entity.investigation : undefined);
      const res = await apiService.getEntity(entity.id, investigationId);
      if (!res.success || !res.data) {
        setPageError(res.message || 'No se pudo cargar la entidad.');
        return;
      }
      setSelectedEntity(res.data);
      setShowViewModal(true);
    };
    void open();
  };

  const handleEdit = (entity: Entity) => {
    const investigationId = entity.investigationId ?? (typeof entity.investigation === 'string' ? entity.investigation : '');
    setSelectedEntity(entity);
    setFormEntity({
      investigationId: investigationId || '',
      name: entity.name || '',
      type: entity.type,
      value: entity.value || '',
      description: entity.description || '',
      propertiesText: JSON.stringify(entity.properties || {}, null, 2),
    });
    setShowEditModal(true);
  };

  const handleDelete = async (entity: Entity) => {
    const result = await Swal.fire({
      title: '¿Estás seguro?',
      text: `¿Está seguro de que desea eliminar la entidad "${entity.name}"?`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (result.isConfirmed) {
      const investigationId = entity.investigationId ?? (typeof entity.investigation === 'string' ? entity.investigation : undefined);
      if (!investigationId) {
        Swal.fire('Error', 'La entidad no tiene investigación asociada.', 'error');
        return;
      }
      const res = await apiService.deleteEntity(entity.id, investigationId);
      if (!res.success) {
        Swal.fire('Error', res.message || 'No se pudo eliminar la entidad.', 'error');
        return;
      }
      Swal.fire('¡Eliminado!', 'La entidad ha sido eliminada.', 'success');
      await loadEntities();
    }
  };

  const loadEntities = async () => {
    try {
      const res = await apiService.getEntities();
      if (!res.success) {
        setEntities([]);
        setPageError(res.message || 'No se pudieron cargar las entidades.');
        return;
      }
      setEntities(res.data || []);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : 'No se pudieron cargar las entidades.');
    }
  };

  const loadInvestigations = async () => {
    try {
      const res = await apiService.getInvestigations();
      if (!res.success) {
        setInvestigationOptions([]);
        return;
      }
      const payload: any = res.data;
      const items = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.results)
          ? payload.results
          : [];
      const mapped = items
        .map((inv: any) => ({
          id: String(inv?.id ?? ''),
          name: String(inv?.name ?? inv?.title ?? 'Sin nombre'),
        }))
        .filter((inv: any) => inv.id);
      setInvestigationOptions(mapped);
    } catch {
      setInvestigationOptions([]);
    }
  };

  const resetForm = () => {
    setFormEntity({
      investigationId: '',
      name: '',
      type: 'domain',
      value: '',
      description: '',
      propertiesText: '{}',
    });
  };

  const saveEntity = (mode: 'create' | 'edit') => {
    const run = async () => {
      setPageError(null);
      const investigationId = formEntity.investigationId.trim();
      if (!investigationId) {
        setPageError('Seleccione una investigación.');
        return;
      }

      let properties: Record<string, any> = {};
      try {
        properties = formEntity.propertiesText ? JSON.parse(formEntity.propertiesText) : {};
      } catch {
        setPageError('Propiedades debe ser un JSON válido.');
        return;
      }

      const value = formEntity.value.trim() || formEntity.name.trim();
      if (!value) {
        setPageError('El valor o nombre de la entidad es obligatorio.');
        return;
      }

      if (mode === 'create') {
        const res = await apiService.createEntity(
          {
            name: formEntity.name.trim() || value,
            type: formEntity.type,
            value,
            description: formEntity.description.trim(),
            properties,
          },
          investigationId
        );
        if (!res.success) {
          setPageError(res.message || 'No se pudo crear la entidad.');
          return;
        }
        setShowModal(false);
      } else if (selectedEntity) {
        const res = await apiService.updateEntity(
          selectedEntity.id,
          {
            name: formEntity.name.trim() || value,
            type: formEntity.type,
            value,
            description: formEntity.description.trim(),
            properties,
          },
          investigationId
        );
        if (!res.success) {
          setPageError(res.message || 'No se pudo actualizar la entidad.');
          return;
        }
        setShowEditModal(false);
        setSelectedEntity(null);
      }

      resetForm();
      await loadEntities();
    };
    void run();
  };

  return (
    <div className="app-shell">
      <Header user={user} onLogout={onLogout} />

      <Container fluid className="app-page py-4">
        {pageError && (
          <Row className="mb-3">
            <Col>
              <Alert variant="danger" className="mb-0">
                {pageError}
              </Alert>
            </Col>
          </Row>
        )}
        <Row className="mb-4">
          <Col>
            <h4 className="mb-3">
              <i className="bi bi-diagram-3 me-2"></i>
              Entidades
            </h4>
          </Col>
        </Row>

        {/* Estadísticas */}
        <Row className="mb-4">
          <Col md={3}>
            <Card className="text-center h-100">
              <Card.Body>
                <i className="bi bi-diagram-3 text-primary" style={{ fontSize: '2rem' }}></i>
                <h5 className="mt-2">{entities.length}</h5>
                <p className="text-muted mb-0">Total Entidades</p>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3}>
            <Card className="text-center h-100">
              <Card.Body>
                <i className="bi bi-people text-success" style={{ fontSize: '2rem' }}></i>
                <h5 className="mt-2">{entities.filter(e => e.type === 'person').length}</h5>
                <p className="text-muted mb-0">Personas</p>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3}>
            <Card className="text-center h-100">
              <Card.Body>
                <i className="bi bi-building text-warning" style={{ fontSize: '2rem' }}></i>
                <h5 className="mt-2">{entities.filter(e => e.type === 'organization').length}</h5>
                <p className="text-muted mb-0">Organizaciones</p>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3}>
            <Card className="text-center h-100">
              <Card.Body>
                <i className="bi bi-globe text-info" style={{ fontSize: '2rem' }}></i>
                <h5 className="mt-2">{entities.filter(e => e.type === 'ip' || e.type === 'domain').length}</h5>
                <p className="text-muted mb-0">Red/Dominios</p>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Filtros y Búsqueda */}
        <Row className="mb-4">
          <Col>
            <Card>
              <Card.Body>
                <Row className="g-3">
                  <Col md={4}>
                    <InputGroup>
                      <InputGroup.Text>
                        <i className="bi bi-search"></i>
                      </InputGroup.Text>
                      <Form.Control
                        type="text"
                        placeholder="Buscar entidades..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                    </InputGroup>
                  </Col>
                  <Col md={4}>
                    <Form.Select
                      value={typeFilter}
                      onChange={(e) => setTypeFilter(e.target.value)}
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
                    <Button variant="primary" className="w-100" onClick={() => { resetForm(); setShowModal(true); }}>
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
            <Card>
              <Card.Body className="p-0">
                <Table responsive hover className="mb-0">
                  <thead>
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

        <Modal show={showViewModal} onHide={() => setShowViewModal(false)} size="lg" centered>
          <Modal.Header closeButton>
            <Modal.Title>
              <i className="bi bi-eye me-2"></i>
              Detalle de Entidad
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {selectedEntity && (
              <div className="d-grid gap-3">
                <div>
                  <div className="text-secondary small">Nombre</div>
                  <div>{selectedEntity.name}</div>
                </div>
                <div>
                  <div className="text-secondary small">Tipo</div>
                  <div>{getTypeText(selectedEntity.type)}</div>
                </div>
                <div>
                  <div className="text-secondary small">Valor</div>
                  <div>{selectedEntity.value || 'N/A'}</div>
                </div>
                <div>
                  <div className="text-secondary small">Descripción</div>
                  <div>{selectedEntity.description || 'Sin descripción'}</div>
                </div>
                <div>
                  <div className="text-secondary small">Propiedades</div>
                  <pre className="bg-dark rounded p-2 mb-0" style={{ whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(selectedEntity.properties || {}, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowViewModal(false)}>
              Cerrar
            </Button>
          </Modal.Footer>
        </Modal>

        {/* Modal para Nueva Entidad */}
        <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" centered>
          <Modal.Header closeButton>
            <Modal.Title>
              <i className="bi bi-plus-circle me-2"></i>
              Nueva Entidad
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <Form>
              <Row className="g-3">
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>Nombre</Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="Ingrese el nombre de la entidad"
                      value={formEntity.name}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, name: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>Tipo</Form.Label>
                    <Form.Select
                      value={formEntity.type}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, type: e.target.value as Entity['type'] }))}
                    >
                      <option value="person">Persona</option>
                      <option value="organization">Organización</option>
                      <option value="ip">Dirección IP</option>
                      <option value="domain">Dominio</option>
                      <option value="email">Email</option>
                      <option value="url">URL</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>Investigación</Form.Label>
                    <Form.Select
                      value={formEntity.investigationId}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, investigationId: e.target.value }))}
                    >
                      <option value="">Seleccionar investigación</option>
                      {investigationOptions.map((inv) => (
                        <option key={inv.id} value={inv.id}>
                          {inv.name}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>Valor</Form.Label>
                    <Form.Control
                      type="text"
                      placeholder="ejemplo.com, 192.168.1.1, user@domain.com..."
                      value={formEntity.value}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, value: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>Descripción</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={3}
                      placeholder="Describa la entidad y su relevancia"
                      value={formEntity.description}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, description: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>Propiedades (JSON)</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={4}
                      placeholder='{"source":"manual"}'
                      value={formEntity.propertiesText}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, propertiesText: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
              </Row>
            </Form>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowModal(false)}>
              Cancelar
            </Button>
            <Button variant="primary" onClick={() => saveEntity('create')}>
              <i className="bi bi-check-circle me-1"></i>
              Crear Entidad
            </Button>
          </Modal.Footer>
        </Modal>

        <Modal show={showEditModal} onHide={() => setShowEditModal(false)} size="lg" centered>
          <Modal.Header closeButton>
            <Modal.Title>
              <i className="bi bi-pencil me-2"></i>
              Editar Entidad
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <Form>
              <Row className="g-3">
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>Nombre</Form.Label>
                    <Form.Control
                      type="text"
                      value={formEntity.name}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, name: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>Tipo</Form.Label>
                    <Form.Select
                      value={formEntity.type}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, type: e.target.value as Entity['type'] }))}
                    >
                      <option value="person">Persona</option>
                      <option value="organization">Organización</option>
                      <option value="ip">Dirección IP</option>
                      <option value="domain">Dominio</option>
                      <option value="email">Email</option>
                      <option value="url">URL</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group>
                    <Form.Label>Investigación</Form.Label>
                    <Form.Select
                      value={formEntity.investigationId}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, investigationId: e.target.value }))}
                    >
                      <option value="">Seleccionar investigación</option>
                      {investigationOptions.map((inv) => (
                        <option key={inv.id} value={inv.id}>
                          {inv.name}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>Valor</Form.Label>
                    <Form.Control
                      type="text"
                      value={formEntity.value}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, value: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>Descripción</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={3}
                      value={formEntity.description}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, description: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
                <Col md={12}>
                  <Form.Group>
                    <Form.Label>Propiedades (JSON)</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={4}
                      value={formEntity.propertiesText}
                      onChange={(e) => setFormEntity(prev => ({ ...prev, propertiesText: e.target.value }))}
                    />
                  </Form.Group>
                </Col>
              </Row>
            </Form>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowEditModal(false)}>
              Cancelar
            </Button>
            <Button variant="primary" onClick={() => saveEntity('edit')}>
              <i className="bi bi-check-circle me-1"></i>
              Guardar Cambios
            </Button>
          </Modal.Footer>
        </Modal>
      </Container>
    </div>
  );
};

export default EntitiesPage;
