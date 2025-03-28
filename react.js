import React, { useEffect, useState } from "react";
import "./HelloWorld.css";

function HelloWorld() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("http://<YOUR_EC2_PUBLIC_IP>:8080/hello")
      .then(res => res.text())
      .then(data => setMessage(data));
  }, []);

  return (
    <div className="hello-container">
      <h1 className="hello-heading">Welcome to HelloWorld App 👋</h1>
      <p className="hello-message">{message || "Loading..."}</p>
    </div>
  );
}

export default HelloWorld;

=================================================================

.hello-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(to right, #fdfbfb, #ebedee);
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.hello-heading {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 1rem;
}

.hello-message {
  font-size: 1.8rem;
  color: #16a085;
  background-color: #ecf0f1;
  padding: 12px 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
