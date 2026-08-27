import { render, screen } from "@testing-library/react";
import { act } from "react";
import { MemoryRouter } from "react-router";

import i18n, { setLocale } from "../i18n";
import Home from "../pages/Home";

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  );
}

describe("Home", () => {
  it("renders the English homepage", async () => {
    await act(async () => {
      await i18n.changeLanguage("en");
    });
    renderHome();
    expect(screen.getByText("One shared format for BASE exit data.")).toBeInTheDocument();
    expect(screen.getByText(/unverified reference information/)).toBeInTheDocument();
    expect(screen.getByText("Browse the map")).toBeInTheDocument();
  });

  it("renders the French homepage after a locale switch", async () => {
    await act(async () => {
      setLocale("fr");
    });
    renderHome();
    expect(
      screen.getByText("Un format commun pour les données d'exits de BASE."),
    ).toBeInTheDocument();
    expect(screen.getByText(/information de référence non vérifiée/)).toBeInTheDocument();
    expect(screen.getByText("Explorer la carte")).toBeInTheDocument();
  });

  it("persists the chosen locale", async () => {
    await act(async () => {
      setLocale("fr");
    });
    expect(localStorage.getItem("openexit.locale")).toBe("fr");
  });
});
