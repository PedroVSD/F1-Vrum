const API_URL = "http://127.0.0.1:8000/drivers/";

// Elementos
const driverModal = document.getElementById("driverModal");
const driverForm = document.getElementById("driverForm");
const driversList = document.getElementById("drivers-list");

// Controle do Modal
function openModal() {
  driverModal.classList.add("active");
}

function closeModal() {
  driverModal.classList.remove("active");
  driverForm.reset();
}

// 1. Fetch dos pilotos da API FastAPI (GET)
async function fetchDrivers() {
  try {
    const response = await fetch(API_URL);
    if (!response.ok) throw new Error("Erro ao carregar o grid");

    const drivers = await response.json();
    renderDrivers(drivers);
  } catch (error) {
    console.error("Erro de conexão:", error);
    // Dados Mock para teste caso o backend não esteja rodando
    renderDrivers([
      { id: 1, number: 1, first_name: "Max", last_name: "Verstappen", nationality: "Holandês", team_id: 1 },
      { id: 2, number: 16, first_name: "Charles", last_name: "Leclerc", nationality: "Monegasco", team_id: 2 }
    ]);
  }
}

// Renderiza a tabela HTML
function renderDrivers(drivers) {
  driversList.innerHTML = "";

  drivers.forEach((driver) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td class="driver-number">#${driver.number}</td>
      <td><strong>${driver.first_name} ${driver.last_name}</strong></td>
      <td>${driver.nationality}</td>
      <td>Equipe #${driver.team_id}</td>
      <td><button class="btn-secondary" onclick="deleteDriver(${driver.id})">Remover</button></td>
    `;
    driversList.appendChild(row);
  });
}

// 2. Criar Piloto via API FastAPI (POST)
driverForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const payload = {
    first_name: document.getElementById("first_name").value,
    last_name: document.getElementById("last_name").value,
    number: parseInt(document.getElementById("number").value),
    nationality: document.getElementById("nationality").value,
    team_id: parseInt(document.getElementById("team_id").value),
  };

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      closeModal();
      fetchDrivers(); // Atualiza a lista
    } else {
      alert("Erro ao salvar piloto. Verifique os dados fornecidos.");
    }
  } catch (error) {
    console.error("Erro ao enviar requisicao:", error);
  }
});

// Inicialização
document.addEventListener("DOMContentLoaded", fetchDrivers);
