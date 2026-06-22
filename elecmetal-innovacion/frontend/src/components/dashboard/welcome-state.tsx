interface WelcomeStateProps {
  hasSessions: boolean;
}

export default function WelcomeState({ hasSessions }: WelcomeStateProps) {
  const message = hasSessions
    ? "Selecciona una sesión del panel izquierdo para ver los detalles."
    : "Crea una sesión en el panel izquierdo para comenzar.";

  return (
    <div className="rounded-lg border bg-white p-8 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
        <svg
          className="h-6 w-6 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z"
          />
        </svg>
      </div>
      <p className="text-sm text-gray-500">
        {message}
      </p>
    </div>
  );
}
