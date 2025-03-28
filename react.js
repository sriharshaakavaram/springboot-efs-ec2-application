import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("http://<YOUR_EC2_PUBLIC_IP>:8080/hello")
      .then(res => res.text())
      .then(data => setMessage(data));
  }, []);

  return (
    <div className="App">
      <h1>{message || "Loading..."}</h1>
    </div>
  );
}

export default App;
