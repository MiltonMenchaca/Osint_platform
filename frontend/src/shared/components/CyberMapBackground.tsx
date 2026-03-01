const CyberMapBackground = () => {
  return (
    <div className="cybermap-bg cybermap-bg--green cybermap-bg--globe">
      <iframe
        className="cybermap-bg__iframe"
        width="657"
        height="652"
        src="https://cybermap.kaspersky.com/en/widget/dynamic/dark"
        frameBorder={0}
        title="Kaspersky Cybermap Widget"
      />
      <div className="cybermap-bg__overlay" />
    </div>
  );
};

export default CyberMapBackground;
