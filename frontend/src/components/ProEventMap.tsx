import { useEffect, useMemo, useState } from 'react';
import { Alert, Button, ButtonGroup, Spinner } from 'react-bootstrap';
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

type EventSeverity = 'low' | 'medium' | 'high' | 'critical';

type GeoEvent = {
  id: string;
  title: string;
  kind: 'scan' | 'breach' | 'ioc' | 'login';
  severity: EventSeverity;
  lat: number;
  lng: number;
  timestamp: string;
  source?: string;
};

const severityOrder: Record<EventSeverity, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

const getSeverityColor = (severity: EventSeverity) => {
  if (severity === 'critical') return '#f43f5e';
  if (severity === 'high') return '#f59e0b';
  if (severity === 'medium') return '#22c55e';
  return '#60a5fa';
};

const FitToEvents = ({ events }: { events: GeoEvent[] }) => {
  const map = useMap();

  useEffect(() => {
    if (!events.length) return;
    const bounds = events.map((e) => [e.lat, e.lng] as [number, number]);
    map.fitBounds(bounds, { padding: [18, 18], maxZoom: 4 });
  }, [events, map]);

  return null;
};

export type ProEventMapProps = {
  height?: number | string;
  minSeverity?: EventSeverity;
  onMinSeverityChange?: (value: EventSeverity) => void;
};

const ProEventMap = ({ height = 420, minSeverity = 'low', onMinSeverityChange }: ProEventMapProps) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<GeoEvent[]>([]);

  const mockEvents = useMemo<GeoEvent[]>(() => {
    const now = Date.now();
    const base: Array<Omit<GeoEvent, 'id' | 'timestamp'>> = [
      { title: 'IOC correlacionado', kind: 'ioc', severity: 'high', lat: 40.4168, lng: -3.7038, source: 'feeds' },
      { title: 'Scan masivo detectado', kind: 'scan', severity: 'critical', lat: 51.5074, lng: -0.1278, source: 'nmap' },
      { title: 'Breach index match', kind: 'breach', severity: 'medium', lat: 52.52, lng: 13.405, source: 'hibp' },
      { title: 'Login anómalo', kind: 'login', severity: 'low', lat: 19.4326, lng: -99.1332, source: 'auth' },
      { title: 'IOC correlacionado', kind: 'ioc', severity: 'medium', lat: 37.7749, lng: -122.4194, source: 'feeds' },
      { title: 'Scan masivo detectado', kind: 'scan', severity: 'high', lat: 35.6762, lng: 139.6503, source: 'nmap' },
      { title: 'Login anómalo', kind: 'login', severity: 'low', lat: -33.8688, lng: 151.2093, source: 'auth' },
      { title: 'Breach index match', kind: 'breach', severity: 'high', lat: 48.8566, lng: 2.3522, source: 'dehashed' },
      { title: 'Scan masivo detectado', kind: 'scan', severity: 'medium', lat: -23.5505, lng: -46.6333, source: 'nmap' },
      { title: 'IOC correlacionado', kind: 'ioc', severity: 'critical', lat: 1.3521, lng: 103.8198, source: 'feeds' },
    ];

    return base.map((e, idx) => ({
      ...e,
      id: `evt_${idx + 1}`,
      timestamp: new Date(now - idx * 1000 * 60 * 17).toISOString(),
    }));
  }, []);

  const visibleEvents = useMemo(() => {
    const min = severityOrder[minSeverity];
    return events.filter((e) => severityOrder[e.severity] >= min);
  }, [events, minSeverity]);

  const load = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/events/geo/', { method: 'GET' });
      if (!response.ok) throw new Error('Endpoint no disponible');
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error('Formato inválido');

      const normalized: GeoEvent[] = data
        .map((d: any) => ({
          id: String(d.id ?? crypto.randomUUID()),
          title: String(d.title ?? d.name ?? 'Evento'),
          kind: (d.kind ?? d.type ?? 'ioc') as GeoEvent['kind'],
          severity: (d.severity ?? 'low') as EventSeverity,
          lat: Number(d.lat),
          lng: Number(d.lng),
          timestamp: String(d.timestamp ?? new Date().toISOString()),
          source: d.source ? String(d.source) : undefined,
        }))
        .filter((e) => Number.isFinite(e.lat) && Number.isFinite(e.lng));

      setEvents(normalized.length ? normalized : mockEvents);
    } catch (e) {
      setEvents(mockEvents);
      setError(e instanceof Error ? e.message : 'No se pudo cargar el mapa');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div
        className="d-flex align-items-center justify-content-center rounded-3 border border-dark-700"
        style={{ height, background: 'rgba(255,255,255,0.02)' }}
      >
        <div className="text-center">
          <Spinner animation="border" variant="primary" />
          <div className="text-muted mt-2">Cargando mapa…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="pro-event-map-wrap">
      <div className="d-flex align-items-center justify-content-between mb-2 gap-2 flex-wrap">
        <div className="text-muted small">
          {visibleEvents.length} eventos · tiles: Carto Dark
        </div>
        <div className="d-flex align-items-center gap-2">
          <ButtonGroup size="sm">
            <Button
              variant={minSeverity === 'low' ? 'primary' : 'outline-primary'}
              onClick={() => onMinSeverityChange?.('low')}
            >
              Baja+
            </Button>
            <Button
              variant={minSeverity === 'medium' ? 'primary' : 'outline-primary'}
              onClick={() => onMinSeverityChange?.('medium')}
            >
              Media+
            </Button>
            <Button
              variant={minSeverity === 'high' ? 'primary' : 'outline-primary'}
              onClick={() => onMinSeverityChange?.('high')}
            >
              Alta+
            </Button>
            <Button
              variant={minSeverity === 'critical' ? 'primary' : 'outline-primary'}
              onClick={() => onMinSeverityChange?.('critical')}
            >
              Crítica
            </Button>
          </ButtonGroup>
          <Button size="sm" variant="outline-light" onClick={load}>
            <i className="bi bi-arrow-clockwise me-1"></i>
            Recargar
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="warning" className="py-2 mb-2">
          <div className="small mb-0 d-flex align-items-center justify-content-between gap-2">
            <span>
              <i className="bi bi-exclamation-triangle me-2"></i>
              {error} · usando datos de demo
            </span>
          </div>
        </Alert>
      )}

      <div className="pro-event-map rounded-3 border border-dark-700 overflow-hidden" style={{ height }}>
        <MapContainer
          center={[20, 0]}
          zoom={2}
          minZoom={2}
          maxZoom={8}
          scrollWheelZoom
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors &copy; CARTO'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          <FitToEvents events={visibleEvents} />
          {visibleEvents.map((e) => {
            const color = getSeverityColor(e.severity);
            const radius = e.severity === 'critical' ? 10 : e.severity === 'high' ? 8 : e.severity === 'medium' ? 7 : 6;
            return (
              <CircleMarker
                key={e.id}
                center={[e.lat, e.lng]}
                radius={radius}
                pathOptions={{ color, weight: 1, fillColor: color, fillOpacity: 0.35 }}
              >
                <Tooltip direction="top" offset={[0, -6]} opacity={0.96} permanent={false}>
                  <div style={{ minWidth: 180 }}>
                    <div className="fw-semibold">{e.title}</div>
                    <div className="text-muted small">
                      {e.kind} · {e.severity} · {new Date(e.timestamp).toLocaleString()}
                    </div>
                    {e.source ? <div className="text-muted small">src: {e.source}</div> : null}
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
};

export default ProEventMap;

