"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/button";
import { ApiError, type ArtworkDraft, type Category } from "@/lib/api";

export type ArtworkFormValues = ArtworkDraft & { category: number };

const EMPTY: ArtworkFormValues = {
  title: "",
  description: "",
  category: 0,
  price_xaf: 0,
  stock_quantity: 1,
  dimensions: "",
  materials: "",
  technique: "",
  year_created: null,
  is_unique_piece: true,
};

/**
 * Formulaire d'œuvre (création + édition).
 * Champs alignés sur ArtworkCreateSerializer ; `category` est un entier (id).
 */
export function ArtworkForm({
  categories,
  initial,
  submitLabel,
  onSubmit,
}: {
  categories: Category[];
  initial?: Partial<ArtworkFormValues>;
  submitLabel: string;
  onSubmit: (values: ArtworkFormValues) => Promise<void>;
}) {
  const [values, setValues] = useState<ArtworkFormValues>({ ...EMPTY, ...initial });
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  // Les sous-catégories portent l'arborescence complète — on aplatit pour le select.
  const flat = categories.flatMap((parent) => [
    parent,
    ...parent.children.map((child) => ({ ...child, name_fr: `— ${child.name_fr}` })),
  ]);

  function set<K extends keyof ArtworkFormValues>(key: K, value: ArtworkFormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!values.title.trim() || !values.description.trim() || !values.category) {
      setError("Titre, description et catégorie sont obligatoires.");
      return;
    }
    if (!Number.isInteger(values.price_xaf) || values.price_xaf <= 0) {
      setError("Le prix doit être un entier strictement positif.");
      return;
    }

    setPending(true);
    try {
      await onSubmit(values);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Enregistrement impossible.");
      setPending(false);
    }
  }

  const inputClass = "mt-1 w-full rounded-md border border-border/40 bg-white px-3 py-2";

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl space-y-4">
      <label className="block text-sm">
        <span className="text-text/70">Titre *</span>
        <input
          type="text"
          required
          maxLength={200}
          value={values.title}
          onChange={(e) => set("title", e.target.value)}
          className={inputClass}
        />
      </label>

      <label className="block text-sm">
        <span className="text-text/70">Description *</span>
        <textarea
          required
          rows={5}
          value={values.description}
          onChange={(e) => set("description", e.target.value)}
          className={inputClass}
        />
      </label>

      <label className="block text-sm">
        <span className="text-text/70">Catégorie *</span>
        <select
          required
          value={values.category || ""}
          onChange={(e) => set("category", Number(e.target.value))}
          className={inputClass}
        >
          <option value="" disabled>
            Choisir une catégorie
          </option>
          {flat.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name_fr}
            </option>
          ))}
        </select>
      </label>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="block text-sm">
          <span className="text-text/70">Prix (XAF) *</span>
          <input
            type="number"
            min={1}
            step={1}
            required
            value={values.price_xaf || ""}
            onChange={(e) => set("price_xaf", Number(e.target.value))}
            className={inputClass}
          />
        </label>

        <label className="block text-sm">
          <span className="text-text/70">Stock *</span>
          <input
            type="number"
            min={0}
            step={1}
            required
            value={values.stock_quantity}
            onChange={(e) => set("stock_quantity", Number(e.target.value))}
            className={inputClass}
          />
        </label>

        <label className="block text-sm">
          <span className="text-text/70">Année</span>
          <input
            type="number"
            min={0}
            max={2100}
            value={values.year_created ?? ""}
            onChange={(e) =>
              set("year_created", e.target.value === "" ? null : Number(e.target.value))
            }
            className={inputClass}
          />
        </label>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="block text-sm">
          <span className="text-text/70">Dimensions</span>
          <input
            type="text"
            placeholder="60 × 80 cm"
            value={values.dimensions ?? ""}
            onChange={(e) => set("dimensions", e.target.value)}
            className={inputClass}
          />
        </label>

        <label className="block text-sm">
          <span className="text-text/70">Matériaux</span>
          <input
            type="text"
            value={values.materials ?? ""}
            onChange={(e) => set("materials", e.target.value)}
            className={inputClass}
          />
        </label>

        <label className="block text-sm">
          <span className="text-text/70">Technique</span>
          <input
            type="text"
            value={values.technique ?? ""}
            onChange={(e) => set("technique", e.target.value)}
            className={inputClass}
          />
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm text-text/70">
        <input
          type="checkbox"
          checked={values.is_unique_piece ?? true}
          onChange={(e) => set("is_unique_piece", e.target.checked)}
          className="h-4 w-4 accent-primary"
        />
        Pièce unique
      </label>

      {error ? (
        <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm ink-danger">
          {error}
        </p>
      ) : null}

      <div className="flex gap-3">
        <Button type="submit" disabled={pending}>
          {pending ? "Enregistrement…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
