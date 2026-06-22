interface ProfileCardProps {
  fullName: string;
  role: string;
}

function roleLabel(role: string): string {
  switch (role) {
    case "postulante":
      return "Postulante";
    case "directora":
      return "Directora";
    case "admin":
      return "Administrador";
    default:
      return role;
  }
}

export default function ProfileCard({ fullName, role }: ProfileCardProps) {
  return (
    <div className="rounded-lg border bg-white p-6 shadow-sm">
      <p className="text-sm text-gray-600">
        Bienvenido,{" "}
        <span className="font-medium text-gray-900">{fullName}</span>
      </p>
      <p className="mt-1 text-xs text-gray-400">
        Rol: {roleLabel(role)}
      </p>
    </div>
  );
}
