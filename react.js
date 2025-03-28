import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import HelloWorld from "./HelloWorld";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/helloWorld" element={<HelloWorld />} />
      </Routes>
    </Router>
  );
}

export default App;

=================================================================

import React, { useEffect, useState } from "react";

function HelloWorld() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("http://<YOUR_EC2_PUBLIC_IP>:8080/hello")
      .then(res => res.text())
      .then(data => setMessage(data));
  }, []);

  return <h1>{message || "Loading..."}</h1>;
}

export default HelloWorld;
