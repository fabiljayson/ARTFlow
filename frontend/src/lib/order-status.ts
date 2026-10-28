/** Libellés FR des statuts de commande (mirroir de apps/commerce/models.py). */
const ORDER_STATUS_LABELS: Record<string, string> = {
  PENDING_PAYMENT: "En attente de paiement",
  PAID: "Payée",
  PROCESSING: "En préparation",
  SHIPPED: "Expédiée",
  DELIVERED: "Livrée",
  CANCELLED: "Annulée",
  PARTIALLY_REFUNDED: "Partiellement remboursée",
  REFUNDED: "Remboursée",
};

export function orderStatusLabel(status: string): string {
  return ORDER_STATUS_LABELS[status] ?? status;
}

/** Classe d'encre selon le statut (tokens Clay). */
export function orderStatusInk(status: string): string {
  switch (status) {
    case "PENDING_PAYMENT":
      return "ink-warning";
    case "PAID":
    case "PROCESSING":
    case "SHIPPED":
    case "DELIVERED":
      return "ink-success";
    case "CANCELLED":
    case "REFUNDED":
      return "ink-danger";
    default:
      return "text-text/70";
  }
}
