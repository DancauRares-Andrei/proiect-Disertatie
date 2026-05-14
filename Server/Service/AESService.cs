using System.Text;
using SecureRiscVServer.Service.AES;

namespace SecureRiscVServer.Service
{
    public class AESService
    {
        public byte[] Encrypt(string plaintext, byte[] key, byte[] iv)
        {
            if (plaintext == null)
                throw new ArgumentNullException(nameof(plaintext));

            var plainBytes = Encoding.UTF8.GetBytes(plaintext);
            return Encrypt(plainBytes, key, iv);
        }

        public byte[] Encrypt(byte[] plainBytes, byte[] key, byte[] iv)
        {
            ValidateInputs(plainBytes, key, iv);

            return AesCbc.Encrypt(plainBytes, key, iv);
        }

        private static void ValidateInputs(byte[] data, byte[] key, byte[] iv)
        {
            if (data == null || data.Length == 0)
                throw new ArgumentException("Nu am primit date");

            if (key == null || key.Length != 16)
                throw new ArgumentException("Cheia AES-128 trebuie sa aiba exact 16 octeti");

            if (iv == null || iv.Length != 16)
                throw new ArgumentException("IV trebuie sa aiba 16 octeti");
        }
    }
}
