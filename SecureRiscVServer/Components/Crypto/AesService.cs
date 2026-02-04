using System.Text;
using SecureRiscVServer.Components.Crypto.AES;

namespace SecureRiscVServer.Components.Crypto
{
    public class AESService
    {
        // =========================
        // Encrypt string (UTF-8)
        // =========================
        public byte[] Encrypt(string plaintext, byte[] key, byte[] iv)
        {
            if (plaintext == null)
                throw new ArgumentNullException(nameof(plaintext));

            var plainBytes = Encoding.UTF8.GetBytes(plaintext);
            return Encrypt(plainBytes, key, iv);
        }

        // =========================
        // Encrypt byte[]
        // =========================
        public byte[] Encrypt(byte[] plainBytes, byte[] key, byte[] iv)
        {
            ValidateInputs(plainBytes, key, iv);

            return AesCbc.Encrypt(plainBytes, key, iv);
        }

        // =========================
        // Decrypt byte[]
        // =========================
        /*public byte[] Decrypt(byte[] cipherBytes, byte[] key, byte[] iv)
        {
            ValidateInputs(cipherBytes, key, iv);

            return AesCbc.Decrypt(cipherBytes, key, iv);
        }*/

        // =========================
        // Input validation
        // =========================
        private static void ValidateInputs(byte[] data, byte[] key, byte[] iv)
        {
            if (data == null || data.Length == 0)
                throw new ArgumentException("Data is empty");

            if (key == null || key.Length != 16)
                throw new ArgumentException("AES-128 key must be exactly 16 bytes");

            if (iv == null || iv.Length != 16)
                throw new ArgumentException("IV must be exactly 16 bytes");
        }
    }
}
