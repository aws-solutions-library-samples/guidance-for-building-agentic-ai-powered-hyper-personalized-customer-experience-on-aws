import { MessageCircle } from 'lucide-react'
import { Button } from './ui/button'
import { Card, CardContent } from './ui/card'
import { Badge } from './ui/badge'
import { useNavigate } from 'react-router-dom'
import Navbar from './Navbar'
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { setSearchTerm } from '../store/slices/uiSlice';
import { getProductImageUrl, handleImageError } from '../utils/imageUtils';

function Home() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { searchTerm } = useAppSelector((state) => state.ui);

  // Featured products data
  const featuredProducts = [
    {
      id: 'VIT001',
      name: 'Premium Vitamin D3 5000 IU',
      brand: 'WellnessPlus',
      price: 24.99,
      rating: 4.7,
      reviews: 1247,
      image: '/images/VIT001.png',
      category: 'Vitamins'
    },
    {
      id: 'SKIN001',
      name: 'Hyaluronic Acid Serum',
      brand: 'DermaCare',
      price: 34.99,
      rating: 4.6,
      reviews: 1834,
      image: '/images/SKIN001.png',
      category: 'Skincare'
    },
    {
      id: 'OTC001',
      name: 'Ibuprofen 200mg Tablets',
      brand: 'PainRelief Plus',
      price: 12.99,
      rating: 4.5,
      reviews: 1456,
      image: '/images/OTC001.png',
      category: 'Medicine'
    },
    {
      id: 'FIRST001',
      name: 'First Aid Kit Complete',
      brand: 'SafetyFirst',
      price: 29.99,
      rating: 4.7,
      reviews: 1876,
      image: '/images/FIRST001.png',
      category: 'First Aid'
    }
  ];

  const handleSearch = () => {
    if (!searchTerm.trim()) return;
    
    const params = new URLSearchParams();
    params.set('q', searchTerm.trim());
    navigate(`/search?${params.toString()}`);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleSearchTermChange = (newTerm: string) => {
    dispatch(setSearchTerm(newTerm));
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="flex flex-col min-h-screen">
        {/* Navbar */}
        <Navbar
          searchQuery={searchTerm}
          onSearchQueryChange={handleSearchTermChange}
          onSearch={handleSearch}
          onKeyPress={handleKeyPress}
        />

        {/* Main Content */}
        <main className="flex-1">
          {/* Hero Section */}
          <section className="py-16 px-6 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
            <div className="max-w-4xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-100 to-indigo-100 dark:from-blue-900/50 dark:to-indigo-900/50 text-blue-800 dark:text-blue-200 px-4 py-2 rounded-full text-sm font-medium mb-6">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                Trusted by 50,000+ customers
              </div>
              <h1 className="text-4xl md:text-5xl font-semibold tracking-tight text-balance mb-6">
                Your trusted partner in
                <span className="block bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent">health and wellness</span>
              </h1>
              <p className="text-lg text-muted-foreground text-balance mb-8 max-w-2xl mx-auto">
                Discover premium healthcare products, supplements, and wellness essentials 
                from trusted brands, delivered with care.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button size="lg" className="px-8 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg">
                  Shop Now
                </Button>
                <Button variant="outline" size="lg" className="px-8 border-blue-200 dark:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-600">
                  Learn More
                </Button>
              </div>
            </div>
          </section>

          {/* Featured Products */}
          <section className="py-12 px-6 bg-muted/20">
            <div className="max-w-7xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-2xl font-semibold tracking-tight mb-3">Featured Products</h2>
                <p className="text-muted-foreground">Carefully selected essentials for your health</p>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {featuredProducts.map((product) => (
                  <Card key={product.id} className="group cursor-pointer border-0 bg-background shadow-sm hover:shadow-md transition-all duration-300">
                    <div className="aspect-square overflow-hidden bg-muted/30 rounded-t-lg">
                      <img 
                        src={getProductImageUrl(product.image)} 
                        alt={product.name} 
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        onError={(e) => handleImageError(e)}
                      />
                    </div>
                    <CardContent className="p-5">
                      <Badge variant="secondary" className="mb-3 text-xs font-medium">
                        {product.category}
                      </Badge>
                      <h3 className="font-medium text-base mb-1 line-clamp-2 leading-snug">
                        {product.name}
                      </h3>
                      <p className="text-muted-foreground text-sm mb-3">{product.brand}</p>
                      <div className="flex items-center gap-2 mb-4">
                        <div className="flex items-center">
                          <span className="text-sm font-medium">{product.rating}</span>
                          <div className="flex ml-1">
                            {[...Array(5)].map((_, i) => (
                              <div key={i} className="w-3 h-3 text-yellow-400 text-xs">
                                ★
                              </div>
                            ))}
                          </div>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          ({product.reviews})
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <p className="font-semibold text-lg">
                          ${product.price}
                        </p>
                        <Button size="sm" variant="outline" className="text-xs">
                          Add to Cart
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </section>

          {/* Categories */}
          <section className="py-12 px-6">
            <div className="max-w-7xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-2xl font-semibold tracking-tight mb-3">Shop by Category</h2>
                <p className="text-muted-foreground">Find exactly what you need</p>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                {[
                  { name: 'Vitamins', icon: '💊' },
                  { name: 'Skincare', icon: '🧴' },
                  { name: 'Pain Relief', icon: '🩹' },
                  { name: 'Digestive', icon: '🫁' },
                  { name: 'Heart Health', icon: '❤️' },
                  { name: 'Mental Health', icon: '🧠' }
                ].map((category) => (
                  <Card key={category.name} className="cursor-pointer border-0 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 hover:shadow-md transition-all duration-300 hover:scale-105">
                    <CardContent className="p-6 text-center">
                      <div className="text-2xl mb-3">{category.icon}</div>
                      <h3 className="font-medium text-sm text-blue-700 dark:text-blue-300">{category.name}</h3>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </section>

          {/* Best Sellers */}
          <section className="py-12 px-6 bg-muted/20">
            <div className="max-w-7xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-2xl font-semibold tracking-tight mb-3">Best Sellers</h2>
                <p className="text-muted-foreground">Most loved by our customers</p>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {[
                  {
                    id: 'BEST001',
                    name: 'Omega-3 Fish Oil 1000mg',
                    brand: 'PureHealth',
                    price: 19.99,
                    originalPrice: 24.99,
                    rating: 4.8,
                    reviews: 2341,
                    image: '/images/VIT002.png',
                    category: 'Supplements',
                    badge: 'Best Seller'
                  },
                  {
                    id: 'BEST002',
                    name: 'Retinol Anti-Aging Cream',
                    brand: 'YouthGlow',
                    price: 42.99,
                    originalPrice: 54.99,
                    rating: 4.7,
                    reviews: 1987,
                    image: '/images/SKIN002.png',
                    category: 'Anti-Aging',
                    badge: 'Top Rated'
                  },
                  {
                    id: 'BEST003',
                    name: 'Probiotic Complex 50 Billion CFU',
                    brand: 'DigestWell',
                    price: 29.99,
                    originalPrice: 39.99,
                    rating: 4.6,
                    reviews: 1654,
                    image: '/images/HERB001.png',
                    category: 'Digestive Health',
                    badge: 'Customer Choice'
                  }
                ].map((product) => (
                  <Card key={product.id} className="group cursor-pointer border-0 bg-background shadow-sm hover:shadow-md transition-all duration-300">
                    <div className="aspect-square overflow-hidden bg-muted/30 rounded-t-lg relative">
                      <img 
                        src={getProductImageUrl(product.image)} 
                        alt={product.name} 
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        onError={(e) => handleImageError(e)}
                      />
                      <Badge className="absolute top-3 left-3 bg-accent text-accent-foreground text-xs font-medium">
                        {product.badge}
                      </Badge>
                    </div>
                    <CardContent className="p-5">
                      <Badge variant="secondary" className="mb-3 text-xs font-medium">
                        {product.category}
                      </Badge>
                      <h3 className="font-medium text-base mb-1 line-clamp-2 leading-snug">
                        {product.name}
                      </h3>
                      <p className="text-muted-foreground text-sm mb-3">{product.brand}</p>
                      <div className="flex items-center gap-2 mb-4">
                        <div className="flex items-center">
                          <span className="text-sm font-medium">{product.rating}</span>
                          <div className="flex ml-1">
                            {[...Array(5)].map((_, i) => (
                              <div key={i} className="w-3 h-3 text-yellow-400 text-xs">
                                ★
                              </div>
                            ))}
                          </div>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          ({product.reviews})
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-lg">
                            ${product.price}
                          </p>
                          <p className="text-sm text-muted-foreground line-through">
                            ${product.originalPrice}
                          </p>
                        </div>
                        <Button size="sm" variant="outline" className="text-xs">
                          Add to Cart
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </section>

          {/* Why Choose Us */}
          <section className="py-12 px-6 bg-muted/20">
            <div className="max-w-6xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-2xl font-semibold tracking-tight mb-3">Why Choose MedicineMart</h2>
                <p className="text-muted-foreground">Your health and safety are our priorities</p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                {[
                  {
                    icon: '🏥',
                    title: 'Licensed Pharmacy',
                    description: 'Fully licensed with certified pharmacists'
                  },
                  {
                    icon: '🚚',
                    title: 'Fast Delivery',
                    description: 'Same-day delivery for urgent needs'
                  },
                  {
                    icon: '🔒',
                    title: 'Secure & Private',
                    description: 'Bank-level security for your data'
                  },
                  {
                    icon: '💬',
                    title: '24/7 Support',
                    description: 'Expert consultation anytime'
                  }
                ].map((feature, index) => (
                  <div key={index} className="text-center p-6 rounded-xl bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 hover:shadow-lg transition-all duration-300">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 dark:bg-blue-800/50 rounded-full text-2xl mb-4">
                      {feature.icon}
                    </div>
                    <h3 className="font-medium text-base mb-2 text-blue-700 dark:text-blue-300">{feature.title}</h3>
                    <p className="text-muted-foreground text-sm leading-relaxed">{feature.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Newsletter */}
          <section className="py-12 px-6">
            <div className="max-w-7xl mx-auto">
              <hr className="border-border/30 mb-12" />
            </div>
            <div className="max-w-2xl mx-auto text-center">
              <h2 className="text-2xl font-semibold tracking-tight mb-3">Stay Updated</h2>
              <p className="text-muted-foreground mb-8">
                Get health tips, product updates, and exclusive offers
              </p>
              <div className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
                <input 
                  type="email" 
                  placeholder="Enter your email"
                  className="flex-1 px-4 py-2.5 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring/20"
                />
                <Button className="px-6 bg-primary hover:bg-primary/90">Subscribe</Button>
              </div>
              <p className="text-xs text-muted-foreground mt-4">
                Unsubscribe anytime. Privacy policy applies.
              </p>
            </div>
          </section>
        </main>

        {/* Floating Chat Button */}
        <Button
          onClick={() => navigate('/chat')}
          className="fixed bottom-6 right-6 h-12 w-12 rounded-full shadow-lg hover:shadow-xl transition-all duration-200 z-50 bg-accent hover:bg-accent/90"
          size="icon"
        >
          <MessageCircle className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}

export default Home;
