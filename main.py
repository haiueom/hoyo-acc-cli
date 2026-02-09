import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel
from rich import box

# Import komponen Rich
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

load_dotenv()

console = Console()


# --- 1. Definisi Model Data ---
class Account(BaseModel):
    id: int
    name: str
    cookie_token: str
    account_id: int
    created_at: str
    updated_at: str | None = None


# --- 2. API Client Class ---
class HoyoClient:
    def __init__(self, base_url: str, secret_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> Any:
        try:
            data = response.json()
            if not response.is_success:
                error_msg = data.get("error", data.get("message", "Unknown error"))
                raise Exception(f"API Error {response.status_code}: {error_msg}")
            return data.get("data")
        except json.JSONDecodeError as err:
            raise Exception(
                f"Failed to decode response ({response.status_code}): {response.text[:200]}"
            ) from err

    def get_accounts(self) -> list[Account]:
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            resp = client.get("/api/accounts")
            data = self._handle_response(resp)
            return [Account(**item) for item in data]

    def get_account_by_id(self, db_id: int) -> Account:
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            resp = client.get(f"/api/accounts/{db_id}")
            data = self._handle_response(resp)
            return Account(**data)

    def create_account(self, name: str, cookie_token: str, account_id: int) -> Account:
        payload = {"name": name, "cookie_token": cookie_token, "account_id": account_id}
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            resp = client.post("/api/accounts", json=payload)
            data = self._handle_response(resp)
            return Account(**data)

    def update_account(
        self,
        db_id: int,
        name: str | None = None,
        cookie_token: str | None = None,
        account_id: int | None = None,
    ) -> Account:
        payload = {}
        if name:
            payload["name"] = name
        if cookie_token:
            payload["cookie_token"] = cookie_token
        if account_id is not None:
            payload["account_id"] = account_id

        if not payload:
            raise ValueError("Tidak ada data untuk diupdate")

        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            resp = client.put(f"/api/accounts/{db_id}", json=payload)
            data = self._handle_response(resp)
            return Account(**data)

    def delete_account(self, db_id: int) -> int:
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            resp = client.delete(f"/api/accounts/{db_id}")
            data = self._handle_response(resp)
            return int(data["id"])


# --- 3. Fungsi Helper Input (New Feature: Cancel) ---
CANCEL_SIGNAL = "__CANCEL__"


def ask_input(
    label: str, required: bool = True, is_number: bool = False
) -> str | int | None:
    """
    Helper custom untuk input dengan fitur Cancel (0) dan validasi.
    Mengembalikan CANCEL_SIGNAL jika user mengetik 0.
    """
    prompt_text = f"{label} [dim](ketik 0 utk batal)[/dim]"

    while True:
        val = Prompt.ask(prompt_text)

        # Cek Cancel
        if val.strip() == "0":
            console.print("[yellow]Proses dibatalkan.[/yellow]")
            return CANCEL_SIGNAL

        # Cek Empty (Jika required)
        if required and not val.strip():
            console.print("[red]Input tidak boleh kosong![/red]")
            continue

        # Jika optional dan kosong (Hanya tekan enter)
        if not required and not val.strip():
            return None

        # Cek Tipe Angka
        if is_number:
            try:
                return int(val)
            except ValueError:
                console.print("[red]Harus berupa angka valid![/red]")
                continue

        return val


# --- 4. Fungsi Helper Tampilan ---
def display_accounts_table(accounts: list[Account]):
    table = Table(title="Daftar Akun Hoyo", box=box.ROUNDED, header_style="bold cyan")

    table.add_column("ID (DB)", justify="right", style="dim")
    table.add_column("Name", style="bold white")
    table.add_column("Game Account ID", justify="right", style="green")
    table.add_column("Cookie Token", style="magenta", overflow="fold")
    table.add_column("Created At", justify="center", style="dim")

    for acc in accounts:
        table.add_row(
            str(acc.id),
            acc.name,
            str(acc.account_id),
            acc.cookie_token,
            acc.created_at.split("T")[0],
        )
    console.print(table)


def display_account_detail(acc: Account):
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Field", style="bold cyan", justify="right")
    table.add_column("Value", style="white", overflow="fold")

    table.add_row("ID (Database)", str(acc.id))
    table.add_row("Name", acc.name)
    table.add_row("Game Account ID", f"[bold green]{acc.account_id}[/bold green]")
    table.add_row("Cookie Token", f"[magenta]{acc.cookie_token}[/magenta]")
    table.add_row("Created At", acc.created_at)

    updated_val = acc.updated_at if acc.updated_at else "[dim]-[/dim]"
    table.add_row("Updated At", updated_val)

    console.print(
        Panel(
            table, title=f"Detail Akun: {acc.name}", border_style="blue", expand=False
        )
    )


def show_menu():
    console.print("\n[bold cyan]--- Main Menu ---[/bold cyan]")
    console.print("[1] [bold green]List[/bold green] Accounts")
    console.print("[2] [bold yellow]Create[/bold yellow] Account")
    console.print("[3] [bold blue]Update[/bold blue] Account")
    console.print("[4] [bold red]Delete[/bold red] Account")
    console.print("[5] [bold magenta]Detail[/bold magenta] Account")
    console.print("[0] Exit")


# --- 5. Fungsi Aksi CRUD ---
def action_list(client: HoyoClient):
    with console.status("[bold green]Mengambil data...[/bold green]"):
        accounts = client.get_accounts()
    if accounts:
        display_accounts_table(accounts)
    else:
        console.print("[yellow]Tidak ada data akun.[/yellow]")


def action_detail(client: HoyoClient):
    console.print(Panel("Lihat Detail Akun", style="magenta"))

    # Input ID dengan opsi Cancel
    db_id = ask_input("Masukkan ID (DB) akun", is_number=True)
    if db_id == CANCEL_SIGNAL:
        return

    try:
        with console.status("[bold magenta]Mencari akun...[/bold magenta]"):
            acc = client.get_account_by_id(db_id)
        display_account_detail(acc)
    except Exception:
        console.print(
            "[bold red]Gagal:[/bold red] Akun tidak ditemukan atau error server."
        )


def action_create(client: HoyoClient):
    console.print(Panel("Tambah Akun Baru", style="yellow"))

    name = ask_input("Nama Akun")
    if name == CANCEL_SIGNAL:
        return

    cookie = ask_input("Cookie Token")
    if cookie == CANCEL_SIGNAL:
        return

    acc_id = ask_input("Game Account ID (Unique)", is_number=True)
    if acc_id == CANCEL_SIGNAL:
        return

    if Confirm.ask(f"Buat akun [bold]{name}[/bold]?"):
        try:
            with console.status("[bold yellow]Menyimpan...[/bold yellow]"):
                new_acc = client.create_account(name, cookie, acc_id)
            console.print(
                f"[bold green]Sukses![/bold green] Akun dibuat dengan ID DB: {new_acc.id}"
            )
            display_account_detail(new_acc)
        except Exception as e:
            console.print(f"[bold red]Gagal:[/bold red] {e}")


def action_update(client: HoyoClient):
    action_list(client)
    console.print(Panel("Update Akun", style="blue"))

    db_id = ask_input("Masukkan ID (DB) akun yang akan diedit", is_number=True)
    if db_id == CANCEL_SIGNAL:
        return

    console.print(
        "[dim]Tekan Enter (kosongkan) jika tidak ingin mengubah data tersebut[/dim]"
    )

    # Input Optional (required=False)
    new_name = ask_input("Nama Baru", required=False)
    if new_name == CANCEL_SIGNAL:
        return

    new_cookie = ask_input("Cookie Token Baru", required=False)
    if new_cookie == CANCEL_SIGNAL:
        return

    new_acc_id = ask_input("Game Account ID Baru", required=False, is_number=True)
    if new_acc_id == CANCEL_SIGNAL:
        return

    if not new_name and not new_cookie and new_acc_id is None:
        console.print("[yellow]Tidak ada perubahan data. Update dibatalkan.[/yellow]")
        return

    try:
        with console.status("[bold blue]Updating...[/bold blue]"):
            updated = client.update_account(
                db_id, name=new_name, cookie_token=new_cookie, account_id=new_acc_id
            )
        console.print(
            f"[bold green]Sukses![/bold green] Data {updated.name} berhasil diperbarui."
        )
        display_account_detail(updated)
    except Exception as e:
        console.print(f"[bold red]Gagal:[/bold red] {e}")


def action_delete(client: HoyoClient):
    action_list(client)
    console.print(Panel("Hapus Akun", style="red"))

    db_id = ask_input("Masukkan ID (DB) akun yang akan DIHAPUS", is_number=True)
    if db_id == CANCEL_SIGNAL:
        return

    if Confirm.ask(f"[bold red]Yakin ingin menghapus akun ID {db_id}?[/bold red]"):
        try:
            with console.status("[bold red]Deleting...[/bold red]"):
                client.delete_account(db_id)
            console.print(
                f"[bold green]Sukses![/bold green] Akun ID {db_id} telah dihapus."
            )
        except Exception as e:
            console.print(f"[bold red]Gagal:[/bold red] {e}")


# --- 6. Main Loop ---
if __name__ == "__main__":
    API_URL = os.getenv("API_URL", "http://localhost:8787")
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

    client = HoyoClient(base_url=API_URL, secret_key=SECRET_KEY)

    console.print(
        Panel.fit(
            "   Hoyo Account CLI Manager   ",
            style="bold blue",
            subtitle="Powered by Python & Rich",
        )
    )

    while True:
        show_menu()
        choice = Prompt.ask(
            "Pilih menu", choices=["1", "2", "3", "4", "5", "0"], default="1"
        )
        print()

        try:
            if choice == "1":
                action_list(client)
            elif choice == "2":
                action_create(client)
            elif choice == "3":
                action_update(client)
            elif choice == "4":
                action_delete(client)
            elif choice == "5":
                action_detail(client)
            elif choice == "0":
                console.print("[bold cyan]Bye bye![/bold cyan]")
                break
        except Exception as e:
            console.print(f"[bold red]Terjadi Kesalahan Global:[/bold red] {e}")

        console.print("\n" + "-" * 30)
